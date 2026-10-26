from typing import Iterable, List
from app.domain.entities import (
    EngineDecision,
    EvaluationContext,
    OperationStatus,
    RuleOutcome,
)
from app.domain.rules import BusinessRule, get_default_rules


class RuleEngine:
    def __init__(self, rules: Iterable[BusinessRule] | None = None) -> None:
        self._rules: List[BusinessRule] = (
            list(rules) if rules is not None else get_default_rules()
        )

    def register_rule(self, rule: BusinessRule) -> None:
        self._rules.append(rule)

    def evaluate(self, context: EvaluationContext) -> EngineDecision:
        outcomes: List[RuleOutcome] = [
            rule.evaluate(context) for rule in self._rules
        ]

        rejected_reasons = [
            outcome.reason
            for outcome in outcomes
            if outcome.triggered
            and outcome.status == OperationStatus.REJECTED
            and outcome.reason is not None
        ]
        if rejected_reasons:
            return EngineDecision(
                status=OperationStatus.REJECTED,
                reasons=rejected_reasons,
                evaluated_rules=outcomes,
            )

        review_reasons = [
            outcome.reason
            for outcome in outcomes
            if outcome.triggered
            and outcome.status == OperationStatus.PENDING_REVIEW
            and outcome.reason is not None
        ]
        if review_reasons:
            return EngineDecision(
                status=OperationStatus.PENDING_REVIEW,
                reasons=review_reasons,
                evaluated_rules=outcomes,
            )

        return EngineDecision(
            status=OperationStatus.APPROVED,
            reasons=[],
            evaluated_rules=outcomes,
        )
