from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base


class CustomerModel(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(10), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class OperationModel(Base):
    __tablename__ = "operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reasons: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class DecisionAuditLogModel(Base):
    __tablename__ = "decision_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    operation_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    is_simulation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_in_usd: Mapped[float] = mapped_column(Float, nullable=False)
    final_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reasons: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    evaluated_rules: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
