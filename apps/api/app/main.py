import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers.ballot import router as ballot_router
from app.routers.health import router as health_router

app = FastAPI(
    title="What's on My Ballot API",
    summary="Versioned civic-information APIs with evidence and privacy safeguards.",
    version="0.2.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "What's on My Ballot"},
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", os.getenv("PUBLIC_WEB_ORIGIN", "http://localhost:3000")).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    """Return useful validation locations without reflecting submitted values."""
    sanitized = []
    for item in error.errors():
        safe_item = {key: value for key, value in item.items() if key not in {"input", "ctx"}}
        sanitized.append(safe_item)
    return JSONResponse(status_code=422, content={"detail": sanitized})

app.include_router(health_router, prefix="/api/v1")
app.include_router(ballot_router, prefix="/api/v1")
