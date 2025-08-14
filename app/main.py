"""
Main FastAPI application for the Visa and Debit Card Scraper.

This module contains the main FastAPI application with all routes,
middleware, authentication, and configuration setup.
"""

import logging
import structlog
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings
from app.database import init_db, health_check as db_health_check
from app.api.v1.api import api_router
from app.core.auth import get_current_user
from app.utils.security import log_security_event

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Sentry if DSN is provided
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting Visa and Debit Card Scraper application")
    
    try:
        # Initialize database
        init_db()
        logger.info("Database initialized successfully")
        
        # Check database health
        db_status = db_health_check()
        if db_status["status"] == "healthy":
            logger.info("Database health check passed")
        else:
            logger.error(f"Database health check failed: {db_status}")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Visa and Debit Card Scraper application")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Advanced visa and debit card scraper with validation capabilities",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Security
security = HTTPBearer()


# Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Log request
    logger.info(
        "Incoming request",
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "Request completed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=process_time
    )
    
    return response


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Security middleware for request validation and monitoring."""
    try:
        # Log security events for sensitive endpoints
        if any(path in request.url.path for path in ["/api/v1/auth", "/api/v1/scraping", "/api/v1/validation"]):
            log_security_event(
                "api_request",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("user-agent", "unknown")
                },
                "info"
            )
        
        response = await call_next(request)
        
        # Log security events for failed requests
        if response.status_code >= 400:
            log_security_event(
                "api_error",
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "client_ip": request.client.host if request.client else "unknown"
                },
                "warning"
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Security middleware error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["localhost", "127.0.0.1", "0.0.0.0"]
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        exception=str(exc),
        exception_type=type(exc).__name__,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": request.url.path
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status of the application
    """
    try:
        # Check database health
        db_status = db_health_check()
        
        # Overall health status
        overall_healthy = db_status["status"] == "healthy"
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": time.time(),
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "database": db_status,
            "services": {
                "database": db_status["status"],
                "api": "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: Application information
    """
    return {
        "message": "Visa and Debit Card Scraper API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Dependency for getting current user
async def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Dependency for getting current authenticated user.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        return await get_current_user(credentials.credentials)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Protected endpoint example
@app.get("/api/v1/protected")
async def protected_endpoint(current_user = Depends(get_current_user_dependency)):
    """
    Example protected endpoint.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Protected data
    """
    return {
        "message": "This is a protected endpoint",
        "user": current_user.to_dict()
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info("Application startup completed")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Application shutdown completed")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )