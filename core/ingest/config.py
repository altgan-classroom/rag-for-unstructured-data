"""Configuration settings for the ingest module."""
from typing import Optional, Dict, Any, List
from pydantic import Field, validator, field_validator
from pydantic_settings import BaseSettings
from enum import Enum
import os

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"

class IngestConfig(BaseSettings):
    """Configuration for the ingest module."""
    
    # LLM Settings
    LLM_PROVIDER: LLMProvider = Field(
        default=LLMProvider.OPENROUTER,
        description="Default provider for LLM operations"
    )
    LLM_DEFAULT_MODEL: str = Field(
        default="google/gemma-3-27b-it",
        description="Default model to use for LLM operations"
    )
    LLM_DEFAULT_TEMPERATURE: float = Field(
        default=0.7,
        description="Default temperature for LLM generation"
    )
    
    # Provider-specific API keys
    LLM_API_KEYS: Dict[str, str] = Field(
        default_factory=dict,
        description="API keys for different LLM providers"
    )
    
    # Provider-specific settings
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1",
        description="Base URL for OpenRouter API"
    )

    USE_LLM_FOR_IMAGES: bool = Field(
        default=False,
        description="Whether to use LLM for image processing"
    )
    
    # Image Processing
    MIN_IMAGE_SIZE: int = Field(
        default=50,
        description="Minimum size for images to be processed (in kB)"
    )
    
    OCR_LANGUAGES: str = Field(
        default="eng",
        description="Languages for OCR processing (comma-separated)"
    )
    
    # PDF Processing
    PDF_EXTRACT_IMAGES: bool = Field(
        default=True,
        description="Whether to extract images from PDFs"
    )
    
    # Celery Settings
    CELERY_WORKER_CONCURRENCY: int = Field(
        default=4,
        description="Number of worker processes/threads"
    )
    CELERY_TASK_TRACK_STARTED: bool = Field(
        default=True,
        description="Whether to track task start time"
    )
    CELERY_RESULT_EXPIRES: int = Field(
        default=2592000,  # 30 days
        description="Result expiration time (in seconds)"
    )
    CELERY_TASK_TIME_LIMIT: int = Field(
        default=3600,  # 1 hour
        description="Maximum time a task can run (in seconds)"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=3300,  # 55 minutes
        description="Soft time limit before task is killed (in seconds)"
    )
    CELERY_TASK_ACKS_LATE: bool = Field(
        default=True,
        description="Task is acknowledged after execution"
    )
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = Field(
        default=1,
        description="Number of tasks to prefetch per worker"
    )
    
    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL for Redis"
    )
    
    class Config:
        env_prefix = "INGEST_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def llm_api_key(self) -> str:
        """Get the API key for the current provider."""
        return self.LLM_API_KEYS.get(self.LLM_PROVIDER.value, "")
    
    @field_validator('LLM_API_KEYS', mode='before')
    @classmethod
    def parse_env_var(cls, v):
        """Parse environment variables for LLM_API_KEYS."""
        if isinstance(v, str):
            # Handle the case where LLM_API_KEYS is passed as a JSON string
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return v or {}

# Create a singleton instance
config = IngestConfig()
