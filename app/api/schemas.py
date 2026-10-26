from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.domain.entities import OperationStatus, RiskLevel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(default="admin", examples=["admin"])
    password: str = Field(default="admin123", examples=["admin123"])


class CustomerCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Juan Perez"])
    country: str = Field(min_length=2, max_length=10, examples=["PY"])
    risk_level: RiskLevel = Field(examples=[RiskLevel.LOW])


class CustomerUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=10)
    risk_level: RiskLevel | None = Field(
        default=None, examples=[RiskLevel.HIGH]
    )


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    country: str
    risk_level: RiskLevel
    created_at: datetime


class OperationCreateRequest(BaseModel):
    customer_id: UUID = Field(
        examples=["1e7dc657-96ef-454e-b3db-05acfe5ec34c"]
    )
    amount: float = Field(examples=[1200.0])
    currency: str = Field(
        default="USD", min_length=3, max_length=10, examples=["USD"]
    )
    operation_type: str = Field(
        default="TRANSFER", min_length=1, max_length=50, examples=["TRANSFER"]
    )


class OperationEvaluationResponse(BaseModel):
    operation_id: UUID
    status: OperationStatus
    reasons: List[str]


class OperationDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    amount: float
    currency: str
    operation_type: str
    status: OperationStatus
    reasons: List[str]
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation_id: UUID
    customer_id: UUID
    is_simulation: bool
    amount: float
    currency: str
    amount_in_usd: float
    final_status: OperationStatus
    reasons: List[str]
    evaluated_rules: List[Dict[str, Any]]
    created_at: datetime
