from fastapi import APIRouter

router = APIRouter(tags=["operational"])


@router.get("/health/live", summary="Liveness check", response_model=dict[str, str])
def live() -> dict[str, str]:
    """Report whether this API process is running."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness check", response_model=dict[str, str])
def ready() -> dict[str, str]:
    """A database-aware readiness check will replace this during persistence work."""
    return {"status": "ready"}
