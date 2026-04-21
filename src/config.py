"""
Configuration Module
Loads settings from environment variables.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    qwen_api_key: str 
    qwen_base_url: str 
    default_model: str 
    code_model: str 
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    streamlit_port: int = 8501
    
    # Data directories
    sessions_dir: str = "data/sessions"
    exports_dir: str = "data/exports"
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False 
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    try:
        return Settings()
    except Exception as e:
        print(f"Error loading settings: {e}")
        raise e