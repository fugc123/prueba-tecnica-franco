from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.application.rule_engine import RuleEngine
from app.domain.entities import (
    CustomerEntity,
    EngineDecision,
    EvaluationContext,
    OperationCandidate,
    RiskLevel,
)
from app.infrastructure.models import (
    CustomerModel,
    DecisionAuditLogModel,
    OperationModel,
)


CURRENCY_TO_USD_RATES: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.10,
    "PYG": 0.00013,
    "ARS": 0.001,
    "BRL": 0.20,
}


def convert_to_usd(amount: float, currency: str) -> float:
    rate = CURRENCY_TO_USD_RATES.get(currency.upper(), 1.0)
    return round(amount * rate, 4)


class CustomerService:
    def create_customer(
        self,
        db: Session,
        name: str,
        country: str,
        risk_level: RiskLevel,
    ) -> CustomerModel:
        now = datetime.now(timezone.utc)
        customer = CustomerModel(
            id=str(uuid4()),
            name=name,
            country=country.upper(),
            risk_level=risk_level.value,
            created_at=now,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    def get_customer(self, db: Session, customer_id: UUID) -> CustomerModel:
        customer = db.get(CustomerModel, str(customer_id))
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found",
            )
        return customer

    def list_customers(self, db: Session) -> List[CustomerModel]:
        stmt = select(CustomerModel).order_by(CustomerModel.created_at.desc())
        return list(db.scalars(stmt).all())

    def update_customer(
        self,
        db: Session,
        customer_id: UUID,
        name: str | None = None,
        country: str | None = None,
        risk_level: RiskLevel | None = None,
    ) -> CustomerModel:
        customer = self.get_customer(db, customer_id)
        if name is not None:
            customer.name = name
        if country is not None:
            customer.country = country.upper()
        if risk_level is not None:
            customer.risk_level = risk_level.value
        db.commit()
        db.refresh(customer)
        return customer


class OperationService:
    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self.rule_engine = rule_engine or RuleEngine()
        self.customer_service = CustomerService()

    def _build_context(
        self, db: Session, candidate: OperationCandidate
    ) -> EvaluationContext:
        customer_model = self.customer_service.get_customer(
            db, candidate.customer_id
        )
        one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        count_stmt = (
            select(func.count())
            .select_from(OperationModel)
            .where(
                OperationModel.customer_id == str(candidate.customer_id),
                OperationModel.created_at >= one_minute_ago,
            )
        )
        recent_count = int(db.scalar(count_stmt) or 0)
        customer_entity = CustomerEntity(
            id=UUID(customer_model.id),
            name=customer_model.name,
            country=customer_model.country,
            risk_level=RiskLevel(customer_model.risk_level),
            created_at=customer_model.created_at,
        )
        return EvaluationContext(
            customer=customer_entity,
            operation=candidate,
            recent_operations_count=recent_count,
            amount_in_usd=convert_to_usd(candidate.amount, candidate.currency),
        )

    def _serialize_outcomes(
        self, decision: EngineDecision
    ) -> List[Dict[str, Any]]:
        return [
            {
                "rule_name": outcome.rule_name,
                "triggered": outcome.triggered,
                "status": outcome.status.value if outcome.status else None,
                "reason": outcome.reason,
            }
            for outcome in decision.evaluated_rules
        ]

    def create_operation(
        self,
        db: Session,
        idempotency_key: str,
        candidate: OperationCandidate,
    ) -> Dict[str, Any]:
        existing_stmt = select(OperationModel).where(
            OperationModel.idempotency_key == idempotency_key
        )
        existing_operation = db.scalar(existing_stmt)
        if existing_operation is not None:
            return {
                "operation_id": UUID(existing_operation.id),
                "status": existing_operation.status,
                "reasons": list(existing_operation.reasons),
            }

        context = self._build_context(db, candidate)
        decision = self.rule_engine.evaluate(context)
        now = datetime.now(timezone.utc)
        operation_id = str(uuid4())

        operation_model = OperationModel(
            id=operation_id,
            customer_id=str(candidate.customer_id),
            amount=candidate.amount,
            currency=candidate.currency.upper(),
            operation_type=candidate.operation_type.upper(),
            status=decision.status.value,
            reasons=decision.reasons,
            idempotency_key=idempotency_key,
            created_at=now,
        )
        audit_log = DecisionAuditLogModel(
            id=str(uuid4()),
            operation_id=operation_id,
            customer_id=str(candidate.customer_id),
            is_simulation=False,
            amount=candidate.amount,
            currency=candidate.currency.upper(),
            amount_in_usd=context.amount_in_usd,
            final_status=decision.status.value,
            reasons=decision.reasons,
            evaluated_rules=self._serialize_outcomes(decision),
            created_at=now,
        )
        db.add(operation_model)
        db.add(audit_log)
        db.commit()

        return {
            "operation_id": UUID(operation_id),
            "status": decision.status.value,
            "reasons": decision.reasons,
        }

    def simulate_operation(
        self,
        db: Session,
        candidate: OperationCandidate,
    ) -> Dict[str, Any]:
        context = self._build_context(db, candidate)
        decision = self.rule_engine.evaluate(context)
        return {
            "operation_id": uuid4(),
            "status": decision.status.value,
            "reasons": decision.reasons,
        }

    def get_operation(
        self, db: Session, operation_id: UUID
    ) -> OperationModel:
        operation = db.get(OperationModel, str(operation_id))
        if operation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found",
            )
        return operation

    def list_audit_logs(
        self, db: Session, customer_id: UUID | None = None
    ) -> List[DecisionAuditLogModel]:
        stmt = select(DecisionAuditLogModel).order_by(
            DecisionAuditLogModel.created_at.desc()
        )
        if customer_id is not None:
            stmt = stmt.where(
                DecisionAuditLogModel.customer_id == str(customer_id)
            )
        return list(db.scalars(stmt).all())
