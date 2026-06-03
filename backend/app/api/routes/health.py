from datetime import UTC, datetime

from fastapi import APIRouter
from neo4j import GraphDatabase
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import engine
from app.schemas.common import HealthResponse, HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        service="api",
        status=HealthStatus.ok,
        checked_at=datetime.now(UTC),
        detail="API process is running",
    )


@router.get("/health/db", response_model=HealthResponse)
def database_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service="postgresql",
        status=_check_postgresql(),
        checked_at=datetime.now(UTC),
        detail=f"Connection check against {settings.database_url} is available",
    )


@router.get("/health/neo4j", response_model=HealthResponse)
def neo4j_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service="neo4j",
        status=_check_neo4j(),
        checked_at=datetime.now(UTC),
        detail=f"Connectivity check against {settings.neo4j_uri} is available",
    )


@router.get("/health/cache", response_model=HealthResponse)
def cache_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service="redis",
        status=_check_redis(),
        checked_at=datetime.now(UTC),
        detail=f"Connectivity check against {settings.redis_url} is available",
    )


def _check_postgresql() -> HealthStatus:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return HealthStatus.failed
    return HealthStatus.ok


def _check_neo4j() -> HealthStatus:
    settings = get_settings()
    try:
        driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))
        with driver.session() as session:
            session.run("RETURN 1 AS ok").consume()
        driver.close()
    except Exception:
        return HealthStatus.failed
    return HealthStatus.ok


def _check_redis() -> HealthStatus:
    settings = get_settings()
    try:
        client = Redis.from_url(settings.redis_url)
        client.ping()
        client.close()
    except Exception:
        return HealthStatus.failed
    return HealthStatus.ok

