"""Configuration management for SOGON API"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class APIConfig:
    """API configuration settings"""
    
    def __init__(self):
        self.host: str = os.getenv("API_HOST", "127.0.0.1")
        self.port: int = int(os.getenv("API_PORT", "8000"))
        self.debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"
        self.log_level: str = os.getenv("API_LOG_LEVEL", "INFO")
        
        # SOGON specific settings
        self.base_output_dir: str = os.getenv("SOGON_OUTPUT_DIR", "./result")
        self.enable_correction: bool = os.getenv("SOGON_ENABLE_CORRECTION", "true").lower() == "true"
        self.use_ai_correction: bool = os.getenv("SOGON_USE_AI_CORRECTION", "true").lower() == "true"
        
    def __repr__(self) -> str:
        return f"APIConfig(host={self.host}, port={self.port}, debug={self.debug})"


# Global config instance
config = APIConfig()
