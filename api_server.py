#!/usr/bin/env python3
"""SOGON API Server entry point"""

import uvicorn
from sogon.api.config import config
from sogon.api.main import app


def main():
    """Start the API server"""
    print(f"Starting SOGON API server on {config.host}:{config.port}")
    print(f"Debug mode: {config.debug}")
    print(f"Access the API documentation at: http://{config.host}:{config.port}/docs")
    
    uvicorn.run(
        "sogon.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )


if __name__ == "__main__":
    main()
