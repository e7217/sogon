"""FastAPI application for SOGON API server"""

import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app instance
app = FastAPI(
    title="SOGON API",
    description="Subtitle generator API from YouTube URLs or local audio files",
    version="1.0.0",
    debug=config.debug
)


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    config: dict


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            config={
                "host": config.host,
                "port": config.port,
                "debug": config.debug,
                "base_output_dir": config.base_output_dir,
                "enable_correction": config.enable_correction,
                "use_ai_correction": config.use_ai_correction
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "SOGON API Server", "docs": "/docs"}


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(_, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting SOGON API server on {config.host}:{config.port}")
    uvicorn.run(
        "sogon.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )
