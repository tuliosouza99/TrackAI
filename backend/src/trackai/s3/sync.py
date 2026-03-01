"""S3 sync operations for TrackAI database."""

from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from trackai.config import load_config


def sync_to_s3(source: Path | None = None) -> None:
    """
    Upload local DuckDB file to S3.

    Args:
        source: Optional path to source file. If not provided, uses default from config.

    Raises:
        ValueError: If S3 storage is not configured
        ClientError: If S3 upload fails
    """
    config = load_config()

    if config.database.storage_type != "s3":
        raise ValueError(
            "S3 storage not configured. Use 'trackai config s3' to configure."
        )

    if not config.database.s3_bucket:
        raise ValueError("S3 bucket not configured")

    if source is None:
        source = Path(config.database.local_cache_path).expanduser()
    else:
        source = Path(source).expanduser()

    if not source.exists():
        raise FileNotFoundError(f"Local database file not found: {source}")

    s3_client = boto3.client("s3")

    try:
        s3_client.upload_file(
            str(source), config.database.s3_bucket, config.database.s3_key
        )
        print(
            f"Successfully uploaded to s3://{config.database.s3_bucket}/{config.database.s3_key}"
        )
    except ClientError as e:
        print(f"Failed to upload to S3: {e}")
        raise


def sync_from_s3(destination: Path | None = None) -> None:
    """
    Download DuckDB file from S3.

    Args:
        destination: Optional path to destination file. If not provided, uses default from config.

    Raises:
        ValueError: If S3 storage is not configured
    """
    config = load_config()

    if config.database.storage_type != "s3":
        return

    if not config.database.s3_bucket:
        raise ValueError("S3 bucket not configured")

    s3_client = boto3.client("s3")

    if destination is None:
        destination = Path(config.database.local_cache_path).expanduser()
    else:
        destination = Path(destination).expanduser()

    destination.parent.mkdir(parents=True, exist_ok=True)

    try:
        s3_client.download_file(
            config.database.s3_bucket, config.database.s3_key, str(destination)
        )
        print(
            f"Successfully downloaded from s3://{config.database.s3_bucket}/{config.database.s3_key}"
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            print("No database found in S3, will create new one")
        else:
            print(f"Failed to download from S3: {e}")
            raise


def check_s3_version_newer() -> bool:
    """
    Check if S3 version is newer than local cache.

    Returns:
        True if S3 version is newer, False otherwise
    """
    config = load_config()
    local_path = Path(config.database.local_cache_path).expanduser()

    if not local_path.exists():
        return True

    local_mtime = datetime.fromtimestamp(local_path.stat().st_mtime, tz=timezone.utc)

    s3_client = boto3.client("s3")
    try:
        response = s3_client.head_object(
            Bucket=config.database.s3_bucket, Key=config.database.s3_key
        )
        s3_mtime = response["LastModified"]

        return s3_mtime > local_mtime
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise


def validate_s3_credentials() -> bool:
    """
    Validate that AWS credentials are available.

    Returns:
        True if credentials are available, False otherwise
    """
    try:
        s3_client = boto3.client("s3")
        # Try to list buckets as a simple validation
        s3_client.list_buckets()
        return True
    except Exception:
        return False
