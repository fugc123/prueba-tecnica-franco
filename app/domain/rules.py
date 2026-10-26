from abc import ABC, abstractmethod
from typing import List
from app.domain.entities import (
    EvaluationContext,
    OperationStatus,
    RiskLevel,
    RuleOutcome,
)


class BusinessRule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        raise NotImplementedError


class InvalidAmountRule(BusinessRule):
    @property
    def name(self) -> str:
        return "INVALID_AMOUNT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if context.operation.amount <= 0:
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.REJECTED,
                reason="INVALID_AMOUNT",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


class HighRiskAmountRule(BusinessRule):
    def __init__(self, max_amount_usd: float = 1000.0) -> None:
        self.max_amount_usd = max_amount_usd

    @property
    def name(self) -> str:
        return "HIGH_RISK_AMOUNT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if (
            context.customer.risk_level == RiskLevel.HIGH
            and context.amount_in_usd > self.max_amount_usd
        ):
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.REJECTED,
                reason="HIGH_RISK_AMOUNT_EXCEEDED",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


class MediumRiskAmountRule(BusinessRule):
    def __init__(self, max_amount_usd: float = 1500.0) -> None:
        self.max_amount_usd = max_amount_usd

    @property
    def name(self) -> str:
        return "MEDIUM_RISK_AMOUNT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if (
            context.customer.risk_level == RiskLevel.MEDIUM
            and context.amount_in_usd > self.max_amount_usd
        ):
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.REJECTED,
                reason="MEDIUM_RISK_AMOUNT_EXCEEDED",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


class LowRiskAmountRule(BusinessRule):
    def __init__(self, max_amount_usd: float = 2000.0) -> None:
        self.max_amount_usd = max_amount_usd

    @property
    def name(self) -> str:
        return "LOW_RISK_AMOUNT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if (
            context.customer.risk_level == RiskLevel.LOW
            and context.amount_in_usd > self.max_amount_usd
        ):
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.REJECTED,
                reason="LOW_RISK_AMOUNT_EXCEEDED",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


class RateLimitRule(BusinessRule):
    def __init__(self, max_operations_per_minute: int = 3) -> None:
        self.max_operations_per_minute = max_operations_per_minute

    @property
    def name(self) -> str:
        return "RATE_LIMIT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if context.recent_operations_count >= self.max_operations_per_minute:
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.REJECTED,
                reason="RATE_LIMIT_EXCEEDED",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


class ManualReviewAmountRule(BusinessRule):
    def __init__(self, threshold_usd: float = 500.0) -> None:
        self.threshold_usd = threshold_usd

    @property
    def name(self) -> str:
        return "MANUAL_REVIEW_AMOUNT_RULE"

    def evaluate(self, context: EvaluationContext) -> RuleOutcome:
        if context.operation.amount > 0 and context.amount_in_usd > self.threshold_usd:
            return RuleOutcome(
                rule_name=self.name,
                triggered=True,
                status=OperationStatus.PENDING_REVIEW,
                reason="MANUAL_REVIEW_REQUIRED",
            )
        return RuleOutcome(rule_name=self.name, triggered=False)


def get_default_rules() -> List[BusinessRule]:
    return [
        InvalidAmountRule(),
        HighRiskAmountRule(),
        MediumRiskAmountRule(),
        LowRiskAmountRule(),
        RateLimitRule(),
        ManualReviewAmountRule(),
    ]
