"""
Configuration Module
Loads settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model: str = "qwen-plus"
    code_model: str = "qwen-coder-plus"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    streamlit_port: int = 8501
    
    # Data directories
    sessions_dir: str = "data/sessions"
    exports_dir: str = "data/exports"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()