"""Configuration management for TrackAI."""

import json
import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration."""

    storage_type: Literal["local", "s3"] = "local"
    mode: Literal["logging", "visualization", "auto"] = "auto"
    db_path: str = str(Path.home() / ".trackai" / "trackai.duckdb")
    s3_bucket: Optional[str] = None
    s3_key: str = "trackai.duckdb"
    s3_region: str = "us-east-1"
    local_cache_path: str = str(Path.home() / ".trackai" / "cache.duckdb")
    sync_interval: int = 300  # seconds


class TrackAIConfig(BaseModel):
    """TrackAI configuration."""

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)


# Configuration file location
CONFIG_DIR = Path.home() / ".trackai"
CONFIG_FILE = CONFIG_DIR / "config.json"
ENV_FILE = CONFIG_DIR / ".env"


def load_config() -> TrackAIConfig:
    """
    Load configuration from file and environment variables.

    Priority: Environment variables > Config file > Defaults

    Returns:
        TrackAIConfig: The loaded configuration
    """
    # Load .env file if it exists
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    config = TrackAIConfig()

    # Load from config file if exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                config = TrackAIConfig(**data)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Warning: Failed to load config file: {e}")
            print("Using default configuration")

    # Override with environment variables
    if os.getenv("TRACKAI_STORAGE_TYPE"):
        storage_type = os.getenv("TRACKAI_STORAGE_TYPE")
        if storage_type in ["local", "s3"]:
            config.database.storage_type = storage_type  # type: ignore

    if os.getenv("TRACKAI_DB_PATH"):
        config.database.db_path = os.getenv("TRACKAI_DB_PATH")  # type: ignore

    if os.getenv("TRACKAI_S3_BUCKET"):
        config.database.s3_bucket = os.getenv("TRACKAI_S3_BUCKET")

    if os.getenv("TRACKAI_S3_KEY"):
        config.database.s3_key = os.getenv("TRACKAI_S3_KEY")  # type: ignore

    if os.getenv("TRACKAI_S3_REGION"):
        config.database.s3_region = os.getenv("TRACKAI_S3_REGION")  # type: ignore

    return config


def save_config(config: TrackAIConfig) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration to save
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


def get_database_config() -> DatabaseConfig:
    """
    Get database configuration.

    Returns:
        DatabaseConfig: Database configuration
    """
    return load_config().database


def update_s3_config(
    bucket: str, key: str = "trackai.duckdb", region: str = "us-east-1"
) -> None:
    """
    Update S3 configuration and switch to S3 storage mode.

    Args:
        bucket: S3 bucket name
        key: S3 object key (path where the database file will be stored within the bucket)
        region: AWS region
    """
    config = load_config()
    config.database.storage_type = "s3"
    config.database.s3_bucket = bucket
    config.database.s3_key = key
    config.database.s3_region = region
    save_config(config)
