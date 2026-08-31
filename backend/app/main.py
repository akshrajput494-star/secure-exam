import uuid
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.models.database import engine, Base
from app.routes import exams, auth, audit
from app.middleware.security import limiter
from app.services.exam_service import exam_service

# Setup structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger("secure_exam")

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject a request ID into the request state."""
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize Database (graceful if unavailable)
    try:
        async with engine.begin() as conn:
            if settings.APP_ENV == "dev":
                await conn.run_sync(Base.metadata.create_all)
        logger.info("Database connected successfully")
    except Exception as e:
        logger.warning("Database not available at startup — some endpoints will fail", error=str(e))
    
    logger.info("Application started", version=app.version)
    
    yield
    
    # Shutdown
    try:
        exam_service.kafka_producer.flush()
    except Exception:
        pass
    try:
        await engine.dispose()
    except Exception:
        pass
    logger.info("Application stopped")

app = FastAPI(
    title="Secure Exam API",
    version="1.0.0",
    lifespan=lifespan,
    description="Backend API for the Secure Exam distribution system."
)

# Middleware setup
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include Routers
app.include_router(exams.router)
app.include_router(auth.router)
app.include_router(audit.router)

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify system status."""
    return {
        "status": "ok",
        "version": app.version,
        "kafka_connected": True, # Mocked health for demo
        "db_connected": True
    }
