import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.routes import router as api_router
from app.config import settings

# Configure logger
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level=settings.LOG_LEVEL,
    backtrace=True,
    diagnose=True
)

# Lifespan context manager (replaces on_event handlers)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup logic
    logger.info("Starting RoncreteCrouter API")
    
    # Check for required API keys
    if not settings.GHL_API_TOKEN:
        logger.warning("GoHighLevel API token not set")
    
    if not settings.GOOGLE_API_KEY:
        logger.warning("Google API key not set")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down RoncreteCrouter API")

# Create FastAPI app
app = FastAPI(
    title="RoncreteCrouter",
    description="Appointment scheduling optimization system that integrates GoHighLevel API v2 with Google Routes Optimization API",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
allowed_origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RoncreteCrouter API",
        "version": "1.0.0",
        "description": "Appointment scheduling optimization system",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )


# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
