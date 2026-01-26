"""Configuration management using Pydantic settings."""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    model_name: str = Field(
        default="x-ai/grok-4.1-fast", description="LLM model to use"
    )

    # API Parameters
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Model temperature"
    )
    max_tokens: int = Field(
        default=5000, gt=0, description="Maximum tokens for API response"
    )
    request_timeout: int = Field(
        default=300, gt=0, description="API request timeout in seconds"
    )

    # Processing Limits
    max_pages: int = Field(default=500, gt=0, description="Maximum PDF pages to process")
    extraction_timeout: int = Field(
        default=120, gt=0, description="PDF extraction timeout in seconds"
    )

    # Historical Context
    enable_history: bool = Field(
        default=True, description="Enable historical context from previous summaries"
    )
    max_previous_summaries: int = Field(
        default=10,
        ge=0,
        description="Maximum number of previous summaries to include in context",
    )

    # Master Files
    global_master_path: str = Field(
        default="~/.academic-summaries/_global_master.md",
        description="Path to global master file",
    )
    auto_update_masters: bool = Field(
        default=True, description="Automatically update master files"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(
        default="./logs/app.log", description="Log file path"
    )

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        if not v or v == "sk-or-v1-your-key-here":
            raise ValueError(
                "Invalid OpenRouter API key. Please set OPENROUTER_API_KEY in .env file"
            )
        if not v.startswith("sk-or-"):
            raise ValueError(
                "Invalid OpenRouter API key format. Key must start with 'sk-or-'"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v

    def get_global_master_path(self) -> Path:
        """Get expanded global master file path."""
        return Path(self.global_master_path).expanduser()

    def get_log_file_path(self) -> Optional[Path]:
        """Get expanded log file path."""
        if self.log_file:
            return Path(self.log_file).expanduser()
        return None


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
