from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class OperationStatus(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_REVIEW = "PENDING_REVIEW"


class OperationType(str, Enum):
    TRANSFER = "TRANSFER"
    PAYMENT = "PAYMENT"
    WITHDRAWAL = "WITHDRAWAL"
    INVESTMENT = "INVESTMENT"


@dataclass(frozen=True)
class CustomerEntity:
    id: UUID
    name: str
    country: str
    risk_level: RiskLevel
    created_at: datetime


@dataclass(frozen=True)
class OperationCandidate:
    customer_id: UUID
    amount: float
    currency: str
    operation_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvaluationContext:
    customer: CustomerEntity
    operation: OperationCandidate
    recent_operations_count: int
    amount_in_usd: float


@dataclass(frozen=True)
class RuleOutcome:
    rule_name: str
    triggered: bool
    status: OperationStatus | None = None
    reason: str | None = None


@dataclass(frozen=True)
class EngineDecision:
    status: OperationStatus
    reasons: List[str]
    evaluated_rules: List[RuleOutcome]
