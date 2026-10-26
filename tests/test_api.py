import os
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite:///./test_suite.db"
os.environ["SEED_DATA"] = "false"

from fastapi.testclient import TestClient
from app.infrastructure.database import Base, engine
from app.main import app


def setup_module(module: object = None) -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module(module: object = None) -> None:
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("./test_suite.db"):
        os.remove("./test_suite.db")


client = TestClient(app)


def get_auth_headers() -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unauthenticated_request_is_rejected() -> None:
    response = client.post(
        "/customers",
        json={"name": "Juan Perez", "country": "PY", "risk_level": "LOW"},
    )
    assert response.status_code in (401, 403)


def test_invalid_credentials_rejected() -> None:
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_create_get_and_update_customer() -> None:
    headers = get_auth_headers()
    create_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "Juan Perez", "country": "PY", "risk_level": "LOW"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    customer_id = created["id"]
    assert created["name"] == "Juan Perez"
    assert created["country"] == "PY"
    assert created["risk_level"] == "LOW"

    patch_res = client.patch(
        f"/customers/{customer_id}",
        headers=headers,
        json={"risk_level": "HIGH"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["risk_level"] == "HIGH"

    get_res = client.get(f"/customers/{customer_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["risk_level"] == "HIGH"


def test_high_risk_operation_rejected_and_idempotent() -> None:
    headers = get_auth_headers()
    cust_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "High Risk User", "country": "PY", "risk_level": "HIGH"},
    )
    customer_id = cust_res.json()["id"]

    idem_key = str(uuid4())
    op_headers = {**headers, "Idempotency-Key": idem_key}
    payload = {
        "customer_id": customer_id,
        "amount": 12000,
        "currency": "USD",
        "operation_type": "TRANSFER",
    }

    first_res = client.post("/operations", headers=op_headers, json=payload)
    assert first_res.status_code == 200
    first_body = first_res.json()
    assert first_body["status"] == "REJECTED"
    assert first_body["reasons"] == ["HIGH_RISK_AMOUNT_EXCEEDED"]

    second_res = client.post("/operations", headers=op_headers, json=payload)
    assert second_res.status_code == 200
    second_body = second_res.json()
    assert second_body["operation_id"] == first_body["operation_id"]
    assert second_body["status"] == "REJECTED"
    assert second_body["reasons"] == ["HIGH_RISK_AMOUNT_EXCEEDED"]


def test_low_risk_manual_review_and_get_operation() -> None:
    headers = get_auth_headers()
    cust_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "Low Risk User", "country": "PY", "risk_level": "LOW"},
    )
    customer_id = cust_res.json()["id"]

    op_res = client.post(
        "/operations",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "customer_id": customer_id,
            "amount": 1200,
            "currency": "USD",
            "operation_type": "TRANSFER",
        },
    )
    assert op_res.status_code == 200
    op_data = op_res.json()
    assert op_data["status"] == "PENDING_REVIEW"
    assert op_data["reasons"] == ["MANUAL_REVIEW_REQUIRED"]

    detail_res = client.get(
        f"/operations/{op_data['operation_id']}", headers=headers
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == op_data["operation_id"]
    assert detail["status"] == "PENDING_REVIEW"
    assert detail["reasons"] == ["MANUAL_REVIEW_REQUIRED"]


def test_negative_or_zero_amount_rejected() -> None:
    headers = get_auth_headers()
    cust_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "Valid User", "country": "PY", "risk_level": "LOW"},
    )
    customer_id = cust_res.json()["id"]

    op_res = client.post(
        "/operations",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "customer_id": customer_id,
            "amount": -100,
            "currency": "USD",
            "operation_type": "TRANSFER",
        },
    )
    assert op_res.status_code == 200
    assert op_res.json()["status"] == "REJECTED"
    assert op_res.json()["reasons"] == ["INVALID_AMOUNT"]


def test_simulation_does_not_persist_operation() -> None:
    headers = get_auth_headers()
    cust_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "Sim User", "country": "PY", "risk_level": "HIGH"},
    )
    customer_id = cust_res.json()["id"]

    sim_res = client.post(
        "/operations/simulate",
        headers=headers,
        json={
            "customer_id": customer_id,
            "amount": 12000,
            "currency": "USD",
            "operation_type": "TRANSFER",
        },
    )
    assert sim_res.status_code == 200
    sim_body = sim_res.json()
    assert sim_body["status"] == "REJECTED"
    assert sim_body["reasons"] == ["HIGH_RISK_AMOUNT_EXCEEDED"]

    get_res = client.get(
        f"/operations/{sim_body['operation_id']}", headers=headers
    )
    assert get_res.status_code == 404


def test_rate_limit_rule_rejects_fourth_operation_within_minute() -> None:
    headers = get_auth_headers()
    cust_res = client.post(
        "/customers",
        headers=headers,
        json={"name": "Frequent User", "country": "PY", "risk_level": "LOW"},
    )
    customer_id = cust_res.json()["id"]

    for _ in range(3):
        res = client.post(
            "/operations",
            headers={**headers, "Idempotency-Key": str(uuid4())},
            json={
                "customer_id": customer_id,
                "amount": 100,
                "currency": "USD",
                "operation_type": "TRANSFER",
            },
        )
        assert res.status_code == 200
        assert res.json()["status"] == "APPROVED"

    fourth_res = client.post(
        "/operations",
        headers={**headers, "Idempotency-Key": str(uuid4())},
        json={
            "customer_id": customer_id,
            "amount": 100,
            "currency": "USD",
            "operation_type": "TRANSFER",
        },
    )
    assert fourth_res.status_code == 200
    assert fourth_res.json()["status"] == "REJECTED"
    assert fourth_res.json()["reasons"] == ["RATE_LIMIT_EXCEEDED"]


def test_audit_logs_traceability() -> None:
    headers = get_auth_headers()
    logs_res = client.get("/audit-logs", headers=headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert "evaluated_rules" in logs[0]
