"""Initialization command for TrackAI setup."""

import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from trackai.config import CONFIG_DIR, ENV_FILE, load_config, update_s3_config
from trackai.db.connection import init_db
from trackai.migration.sqlite_to_duckdb import (
    check_sqlite_exists,
    migrate_sqlite_to_duckdb,
)
from trackai.s3.sync import sync_to_s3, validate_s3_credentials


def save_aws_credentials(
    access_key: str, secret_key: str, region: str = "us-east-1"
) -> None:
    """
    Save AWS credentials to .env file.

    Args:
        access_key: AWS access key ID
        secret_key: AWS secret access key
        region: AWS region
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing .env file if it exists
    env_content = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_content[key] = value

    # Update AWS credentials
    env_content["AWS_ACCESS_KEY_ID"] = access_key
    env_content["AWS_SECRET_ACCESS_KEY"] = secret_key
    env_content["AWS_DEFAULT_REGION"] = region

    # Write back to .env file
    with open(ENV_FILE, "w") as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")


@click.command()
def init():
    """Initialize TrackAI database configuration."""
    click.echo(click.style("\n🚀 TrackAI Setup Wizard", fg="blue", bold=True))
    click.echo("=" * 50)

    # Check if already configured
    config = load_config()
    if (
        config.database.storage_type != "local"
        or Path(config.database.db_path).expanduser().exists()
    ):
        click.echo(
            click.style("\n⚠️  TrackAI is already configured.", fg="yellow", bold=True)
        )
        if not click.confirm("Do you want to reconfigure?"):
            click.echo("Setup cancelled")
            sys.exit(0)

    # Step 1: Choose storage type
    click.echo(click.style("\n📦 Step 1: Choose Storage Type", fg="cyan", bold=True))
    click.echo("  1. Local - Store database on this machine")
    click.echo("  2. S3 - Store database in AWS S3 (cloud)")

    storage_choice = click.prompt(
        "\nSelect storage type", type=click.IntRange(1, 2), default=1
    )

    if storage_choice == 1:
        # Local storage setup
        click.echo(click.style("\n✓ Selected: Local Storage", fg="green"))

        # Check for existing SQLite database
        sqlite_path = check_sqlite_exists()
        if sqlite_path:
            click.echo(
                click.style(
                    f"\n📄 Found existing SQLite database: {sqlite_path}",
                    fg="yellow",
                )
            )
            if click.confirm("Migrate this database to DuckDB?"):
                click.echo("\nMigrating database...")
                duckdb_path = str(Path(config.database.db_path).expanduser())
                success = migrate_sqlite_to_duckdb(sqlite_path, duckdb_path)
                if success:
                    click.echo(
                        click.style("\n✓ Migration completed!", fg="green", bold=True)
                    )
                else:
                    click.echo(
                        click.style("\n✗ Migration failed!", fg="red", bold=True),
                        err=True,
                    )
                    sys.exit(1)
            else:
                click.echo("Skipping migration. Creating new database...")
                init_db()
        else:
            click.echo("\nCreating new DuckDB database...")
            init_db()

        click.echo(
            click.style(
                f"\n✓ Database initialized at: {config.database.db_path}",
                fg="green",
            )
        )

    else:
        # S3 storage setup
        click.echo(click.style("\n✓ Selected: S3 Storage", fg="green"))

        # Collect AWS credentials first
        click.echo(
            click.style("\n🔑 Step 2: AWS Credentials", fg="cyan", bold=True)
        )
        click.echo("Enter your AWS credentials (they will be saved to ~/.trackai/.env)")

        access_key = click.prompt("AWS Access Key ID")
        secret_key = click.prompt("AWS Secret Access Key", hide_input=True)
        region = click.prompt("AWS Region", default="us-east-1")

        # Save AWS credentials to .env file
        save_aws_credentials(access_key, secret_key, region)
        click.echo(click.style("✓ AWS credentials saved to ~/.trackai/.env", fg="green"))

        # Reload environment variables from .env file
        load_dotenv(ENV_FILE, override=True)

        # Validate AWS credentials
        click.echo("\nValidating AWS credentials...")
        if not validate_s3_credentials():
            click.echo(
                click.style(
                    "\n✗ AWS credentials are invalid!",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
            sys.exit(1)

        click.echo(click.style("✓ AWS credentials validated", fg="green"))

        # Collect S3 configuration
        click.echo(click.style("\n☁️  Step 3: S3 Configuration", fg="cyan", bold=True))
        click.echo(
            click.style(
                "⚠️  Note: The S3 bucket must already exist in your AWS account.",
                fg="yellow",
            )
        )
        click.echo("    You can create it with: aws s3 mb s3://your-bucket-name\n")

        bucket = click.prompt("S3 Bucket name")
        object_key = click.prompt(
            "Object key (path where the database file will be stored within the bucket)",
            default="trackai.duckdb",
        )

        # Update configuration
        update_s3_config(bucket, object_key, region)
        click.echo(click.style("\n✓ S3 configuration saved", fg="green"))

        # Reload config to get updated paths
        config = load_config()
        local_db_path = Path(config.database.db_path).expanduser()
        cache_db_path = Path(config.database.local_cache_path).expanduser()

        # Check for existing local DuckDB database
        if local_db_path.exists() and local_db_path != cache_db_path:
            click.echo(
                click.style(
                    f"\n📄 Found existing local DuckDB database: {local_db_path}",
                    fg="yellow",
                )
            )
            click.echo(f"   Copying to S3 cache location: {cache_db_path}")

            # Copy the database file to cache location
            import shutil
            shutil.copy2(local_db_path, cache_db_path)
            click.echo(click.style("✓ Database copied to cache", fg="green"))

            # Upload to S3
            if click.confirm("Upload database to S3 now?", default=True):
                click.echo("\nUploading to S3...")
                try:
                    sync_to_s3()
                    click.echo(
                        click.style("✓ Uploaded to S3!", fg="green", bold=True)
                    )
                except Exception as e:
                    click.echo(
                        click.style(f"✗ Upload failed: {e}", fg="red"),
                        err=True,
                    )

        # Check for existing SQLite database to migrate
        sqlite_path = check_sqlite_exists()
        if sqlite_path:
            click.echo(
                click.style(
                    f"\n📄 Found existing SQLite database: {sqlite_path}",
                    fg="yellow",
                )
            )
            if click.confirm("Migrate this database to DuckDB?"):
                click.echo("\nMigrating database...")
                config = load_config()  # Reload config
                duckdb_path = str(Path(config.database.local_cache_path).expanduser())
                success = migrate_sqlite_to_duckdb(sqlite_path, duckdb_path)
                if success:
                    click.echo(
                        click.style("\n✓ Migration completed!", fg="green", bold=True)
                    )

                    # Upload to S3
                    if click.confirm("Upload database to S3 now?", default=True):
                        click.echo("\nUploading to S3...")
                        try:
                            sync_to_s3()
                            click.echo(
                                click.style("✓ Uploaded to S3!", fg="green", bold=True)
                            )
                        except Exception as e:
                            click.echo(
                                click.style(f"✗ Upload failed: {e}", fg="red"),
                                err=True,
                            )
                else:
                    click.echo(
                        click.style("\n✗ Migration failed!", fg="red", bold=True),
                        err=True,
                    )
                    sys.exit(1)
            else:
                click.echo("Skipping migration. Creating new database...")
                init_db()
        else:
            click.echo("\nCreating new DuckDB database...")
            init_db()

    # Final summary
    click.echo(click.style("\n" + "=" * 50, fg="blue"))
    click.echo(click.style("✅ Setup Complete!", fg="green", bold=True))
    click.echo("\nNext steps:")
    click.echo("  1. Run 'trackai server start' to start the server")
    click.echo("  2. Run 'trackai config show' to view your configuration")
    if storage_choice == 2:
        click.echo("  3. Run 'trackai db sync' to manually sync with S3")
