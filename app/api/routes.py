from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.api.schemas import (
    AuditLogResponse,
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
    LoginRequest,
    OperationCreateRequest,
    OperationDetailResponse,
    OperationEvaluationResponse,
    TokenResponse,
)
from app.application.services import CustomerService, OperationService
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
)
from app.domain.entities import OperationCandidate
from app.infrastructure.database import get_db

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
customers_router = APIRouter(prefix="/customers", tags=["Customers"])
operations_router = APIRouter(prefix="/operations", tags=["Operations"])
audit_router = APIRouter(prefix="/audit-logs", tags=["Traceability"])

customer_service = CustomerService()
operation_service = OperationService()


@auth_router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=payload.username)
    return TokenResponse(access_token=token)


@customers_router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> CustomerResponse:
    customer = customer_service.create_customer(
        db=db,
        name=payload.name,
        country=payload.country,
        risk_level=payload.risk_level,
    )
    return CustomerResponse.model_validate(customer)


@customers_router.get("", response_model=List[CustomerResponse])
def list_customers(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> List[CustomerResponse]:
    customers = customer_service.list_customers(db=db)
    return [CustomerResponse.model_validate(c) for c in customers]


@customers_router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> CustomerResponse:
    if (
        payload.name is None
        and payload.country is None
        and payload.risk_level is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update",
        )
    customer = customer_service.update_customer(
        db=db,
        customer_id=customer_id,
        name=payload.name,
        country=payload.country,
        risk_level=payload.risk_level,
    )
    return CustomerResponse.model_validate(customer)


@customers_router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> CustomerResponse:
    customer = customer_service.get_customer(db=db, customer_id=customer_id)
    return CustomerResponse.model_validate(customer)


@operations_router.post("", response_model=OperationEvaluationResponse)
def create_operation(
    payload: OperationCreateRequest,
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=100,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    ),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OperationEvaluationResponse:
    candidate = OperationCandidate(
        customer_id=payload.customer_id,
        amount=payload.amount,
        currency=payload.currency,
        operation_type=payload.operation_type,
    )
    result = operation_service.create_operation(
        db=db,
        idempotency_key=idempotency_key,
        candidate=candidate,
    )
    return OperationEvaluationResponse(**result)


@operations_router.post(
    "/simulate", response_model=OperationEvaluationResponse
)
def simulate_operation(
    payload: OperationCreateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OperationEvaluationResponse:
    candidate = OperationCandidate(
        customer_id=payload.customer_id,
        amount=payload.amount,
        currency=payload.currency,
        operation_type=payload.operation_type,
    )
    result = operation_service.simulate_operation(db=db, candidate=candidate)
    return OperationEvaluationResponse(**result)


@operations_router.get(
    "/{operation_id}", response_model=OperationDetailResponse
)
def get_operation(
    operation_id: UUID,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> OperationDetailResponse:
    operation = operation_service.get_operation(
        db=db, operation_id=operation_id
    )
    return OperationDetailResponse.model_validate(operation)


@audit_router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    customer_id: UUID | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
) -> List[AuditLogResponse]:
    logs = operation_service.list_audit_logs(db=db, customer_id=customer_id)
    return [AuditLogResponse.model_validate(item) for item in logs]
