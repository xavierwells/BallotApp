from fastapi import APIRouter, HTTPException, status

from app.database import database_is_ready

router = APIRouter(tags=["operational"])


@router.get("/health/live", summary="Liveness check", response_model=dict[str, str])
def live() -> dict[str, str]:
    """Report whether this API process is running."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check", response_model=dict[str, str])
def ready() -> dict[str, str]:
    """Report whether PostgreSQL is reachable for API work."""
    if not database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return {"status": "ready"}
