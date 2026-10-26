from datetime import datetime, timezone
from uuid import uuid4
from app.application.rule_engine import RuleEngine
from app.domain.entities import (
    CustomerEntity,
    EvaluationContext,
    OperationCandidate,
    OperationStatus,
    RiskLevel,
    RuleOutcome,
)
from app.domain.rules import BusinessRule


def build_context(
    risk_level: RiskLevel = RiskLevel.LOW,
    amount: float = 100.0,
    recent_operations_count: int = 0,
    currency: str = "USD",
) -> EvaluationContext:
    customer_id = uuid4()
    customer = CustomerEntity(
        id=customer_id,
        name="Juan Perez",
        country="PY",
        risk_level=risk_level,
        created_at=datetime.now(timezone.utc),
    )
    operation = OperationCandidate(
        customer_id=customer_id,
        amount=amount,
        currency=currency,
        operation_type="TRANSFER",
    )
    return EvaluationContext(
        customer=customer,
        operation=operation,
        recent_operations_count=recent_operations_count,
        amount_in_usd=amount,
    )


def test_approved_low_risk_small_amount() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(build_context(risk_level=RiskLevel.LOW, amount=300.0))
    assert decision.status == OperationStatus.APPROVED
    assert decision.reasons == []


def test_high_risk_amount_exceeded() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(build_context(risk_level=RiskLevel.HIGH, amount=12000.0))
    assert decision.status == OperationStatus.REJECTED
    assert decision.reasons == ["HIGH_RISK_AMOUNT_EXCEEDED"]


def test_low_risk_amount_exceeded() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(build_context(risk_level=RiskLevel.LOW, amount=2500.0))
    assert decision.status == OperationStatus.REJECTED
    assert decision.reasons == ["LOW_RISK_AMOUNT_EXCEEDED"]


def test_medium_risk_amount_exceeded() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(build_context(risk_level=RiskLevel.MEDIUM, amount=1800.0))
    assert decision.status == OperationStatus.REJECTED
    assert decision.reasons == ["MEDIUM_RISK_AMOUNT_EXCEEDED"]


def test_rate_limit_exceeded() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(
        build_context(risk_level=RiskLevel.LOW, amount=200.0, recent_operations_count=3)
    )
    assert decision.status == OperationStatus.REJECTED
    assert decision.reasons == ["RATE_LIMIT_EXCEEDED"]


def test_manual_review_above_500_usd() -> None:
    engine = RuleEngine()
    decision = engine.evaluate(build_context(risk_level=RiskLevel.LOW, amount=1200.0))
    assert decision.status == OperationStatus.PENDING_REVIEW
    assert decision.reasons == ["MANUAL_REVIEW_REQUIRED"]


def test_zero_or_negative_amount_rejected() -> None:
    engine = RuleEngine()
    zero_decision = engine.evaluate(build_context(amount=0.0))
    neg_decision = engine.evaluate(build_context(amount=-50.0))
    assert zero_decision.status == OperationStatus.REJECTED
    assert zero_decision.reasons == ["INVALID_AMOUNT"]
    assert neg_decision.status == OperationStatus.REJECTED
    assert neg_decision.reasons == ["INVALID_AMOUNT"]


def test_extensibility_custom_rule() -> None:
    class BlockedCountryRule(BusinessRule):
        @property
        def name(self) -> str:
            return "BLOCKED_COUNTRY_RULE"

        def evaluate(self, context: EvaluationContext) -> RuleOutcome:
            if context.customer.country == "XX":
                return RuleOutcome(
                    rule_name=self.name,
                    triggered=True,
                    status=OperationStatus.REJECTED,
                    reason="COUNTRY_RESTRICTED",
                )
            return RuleOutcome(rule_name=self.name, triggered=False)

    engine = RuleEngine()
    engine.register_rule(BlockedCountryRule())
    base_ctx = build_context(risk_level=RiskLevel.LOW, amount=100.0)
    restricted_customer = CustomerEntity(
        id=base_ctx.customer.id,
        name="Test",
        country="XX",
        risk_level=RiskLevel.LOW,
        created_at=base_ctx.customer.created_at,
    )
    ctx = EvaluationContext(
        customer=restricted_customer,
        operation=base_ctx.operation,
        recent_operations_count=0,
        amount_in_usd=100.0,
    )
    decision = engine.evaluate(ctx)
    assert decision.status == OperationStatus.REJECTED
    assert "COUNTRY_RESTRICTED" in decision.reasons
