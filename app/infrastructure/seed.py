from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.entities import OperationStatus, RiskLevel
from app.infrastructure.models import (
    CustomerModel,
    DecisionAuditLogModel,
    OperationModel,
)


SEED_CUSTOMERS = [
    {
        "id": "1e7dc657-96ef-454e-b3db-05acfe5ec34c",
        "name": "Juan Perez",
        "country": "PY",
        "risk_level": RiskLevel.LOW.value,
    },
    {
        "id": "2b8ed768-07fa-465f-a4ec-16bd0f6fd45d",
        "name": "Maria Gomez",
        "country": "AR",
        "risk_level": RiskLevel.MEDIUM.value,
    },
    {
        "id": "3c9fe879-18ab-476a-b5fd-27ce1a7ae56e",
        "name": "Carlos Lopez",
        "country": "BR",
        "risk_level": RiskLevel.HIGH.value,
    },
]


SEED_OPERATIONS = [
    {
        "id": "a1111111-2222-4333-8444-555555555551",
        "customer_id": "1e7dc657-96ef-454e-b3db-05acfe5ec34c",
        "amount": 350.0,
        "currency": "USD",
        "operation_type": "TRANSFER",
        "status": OperationStatus.APPROVED.value,
        "reasons": [],
        "idempotency_key": "seed-idem-key-001",
    },
    {
        "id": "a1111111-2222-4333-8444-555555555552",
        "customer_id": "1e7dc657-96ef-454e-b3db-05acfe5ec34c",
        "amount": 1200.0,
        "currency": "USD",
        "operation_type": "TRANSFER",
        "status": OperationStatus.PENDING_REVIEW.value,
        "reasons": ["MANUAL_REVIEW_REQUIRED"],
        "idempotency_key": "seed-idem-key-002",
    },
    {
        "id": "a1111111-2222-4333-8444-555555555553",
        "customer_id": "3c9fe879-18ab-476a-b5fd-27ce1a7ae56e",
        "amount": 12000.0,
        "currency": "USD",
        "operation_type": "TRANSFER",
        "status": OperationStatus.REJECTED.value,
        "reasons": ["HIGH_RISK_AMOUNT_EXCEEDED"],
        "idempotency_key": "seed-idem-key-003",
    },
]


def seed_initial_data(db: Session) -> None:
    existing = db.scalar(select(CustomerModel.id).limit(1))
    if existing is not None:
        return

    historical_time = datetime.now(timezone.utc) - timedelta(minutes=15)

    for item in SEED_CUSTOMERS:
        db.add(
            CustomerModel(
                id=item["id"],
                name=item["name"],
                country=item["country"],
                risk_level=item["risk_level"],
                created_at=historical_time,
            )
        )

    for op in SEED_OPERATIONS:
        db.add(
            OperationModel(
                id=op["id"],
                customer_id=op["customer_id"],
                amount=op["amount"],
                currency=op["currency"],
                operation_type=op["operation_type"],
                status=op["status"],
                reasons=op["reasons"],
                idempotency_key=op["idempotency_key"],
                created_at=historical_time,
            )
        )
        db.add(
            DecisionAuditLogModel(
                id=f"d{op['id'][1:]}",
                operation_id=op["id"],
                customer_id=op["customer_id"],
                is_simulation=False,
                amount=op["amount"],
                currency=op["currency"],
                amount_in_usd=op["amount"],
                final_status=op["status"],
                reasons=op["reasons"],
                evaluated_rules=[
                    {
                        "rule_name": "SEED_INITIALIZATION",
                        "triggered": len(op["reasons"]) > 0,
                        "status": op["status"],
                        "reason": op["reasons"][0] if op["reasons"] else None,
                    }
                ],
                created_at=historical_time,
            )
        )

    db.commit()
