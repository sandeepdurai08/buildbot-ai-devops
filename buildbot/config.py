"""
BuildBot Configuration Module
Loads settings from environment variables with validation.
Compatible with Python 3.14+
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class JenkinsSettings(BaseSettings):
    """Jenkins connection settings."""
    url: str = Field(default="http://localhost:8080", alias="JENKINS_URL")
    user: str = Field(default="admin", alias="JENKINS_USER")
    api_token: str = Field(default="", alias="JENKINS_API_TOKEN")
    default_job: str = Field(default="HOT_fix_job", alias="JENKINS_DEFAULT_JOB")
    
    model_config = {"extra": "ignore", "populate_by_name": True}


class LLMSettings(BaseSettings):
    """LLM (Exterro) connection settings."""
    url: str = Field(
        default="https://your-llm-endpoint.example.com/v1/chat/completions",
        alias="LLM_URL"
    )
    model: str = Field(
        default="your-model-name",
        alias="LLM_MODEL"
    )
    api_key: str = Field(default="", alias="LLM_API_KEY")
    temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    max_tokens: int = Field(default=1024, alias="LLM_MAX_TOKENS")
    verify_ssl: bool = Field(default=True, alias="LLM_VERIFY_SSL")
    
    model_config = {"extra": "ignore", "populate_by_name": True}


class NotificationSettings(BaseSettings):
    """Notification settings for Google Chat and Email."""
    gchat_webhook_url: str = Field(default="", alias="GCHAT_WEBHOOK_URL")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    smtp_host: str = Field(default="localhost", alias="SMTP_HOST")
    smtp_port: int = Field(default=25, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="buildbot@local.dev", alias="SMTP_FROM")
    smtp_to: str = Field(default="team@example.com", alias="SMTP_TO")
    
    model_config = {"extra": "ignore", "populate_by_name": True}


class AppSettings(BaseSettings):
    """Application settings."""
    artifacts_shared_path: str = Field(
        default="D:\\shared\\builds",
        alias="ARTIFACTS_SHARED_PATH"
    )
    # Use str instead of list[str] to avoid pydantic-settings parsing issues
    allowed_repos: str = Field(default="github.com", alias="ALLOWED_REPOS")
    poll_interval: int = Field(default=5, alias="POLL_INTERVAL")
    debug: bool = Field(default=False, alias="DEBUG")
    
    model_config = {"extra": "ignore", "populate_by_name": True}
    
    def get_allowed_repos_list(self) -> list[str]:
        """Get allowed repos as a list."""
        if not self.allowed_repos:
            return ["github.com"]
        return [r.strip() for r in self.allowed_repos.split(",") if r.strip()]


class Settings(BaseSettings):
    """Main settings container."""
    jenkins: JenkinsSettings = Field(default_factory=JenkinsSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    
    model_config = {"extra": "ignore"}
    
    @property
    def allowed_repos(self) -> list[str]:
        """Convenience property to get allowed repos list."""
        return self.app.get_allowed_repos_list()


# Global settings instance
settings = Settings()
