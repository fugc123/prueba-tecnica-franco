from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from app.api.routes import (
    audit_router,
    auth_router,
    customers_router,
    operations_router,
)
from app.core.config import settings
from app.infrastructure.database import Base, SessionLocal, engine
from app.infrastructure.seed import seed_initial_data


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
    if settings.seed_data:
        db = SessionLocal()
        try:
            seed_initial_data(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(auth_router)
app.include_router(customers_router)
app.include_router(operations_router)
app.include_router(audit_router)
