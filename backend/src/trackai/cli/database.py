"""Database management commands."""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy import create_engine, text

from trackai.config import load_config
from trackai.db.connection import get_db_url
from trackai.migration.sqlite_to_duckdb import (
    check_sqlite_exists,
    migrate_sqlite_to_duckdb,
)
from trackai.s3.sync import sync_to_s3


@click.group(name="db")
def db():
    """Database management commands."""
    pass


@db.command()
def info():
    """Show database statistics."""
    config = load_config()

    click.echo(click.style("Database Information", fg="blue", bold=True))
    click.echo(f"\nStorage Type: {config.database.storage_type}")
    click.echo(f"Mode: {config.database.mode}")

    if config.database.storage_type == "local":
        db_path = Path(config.database.db_path).expanduser()
        click.echo(f"Database Path: {db_path}")

        if not db_path.exists():
            click.echo(click.style("\nDatabase does not exist yet.", fg="yellow"))
            return
    else:
        click.echo(f"S3 Bucket: {config.database.s3_bucket}")
        click.echo(f"S3 Key: {config.database.s3_key}")
        click.echo(f"S3 Region: {config.database.s3_region}")
        db_path = Path(config.database.local_cache_path).expanduser()
        click.echo(f"Local Cache: {db_path}")

        if not db_path.exists():
            click.echo(click.style("\nLocal cache does not exist yet.", fg="yellow"))
            return

    # Show file size
    file_size_mb = db_path.stat().st_size / (1024 * 1024)
    click.echo(f"File Size: {file_size_mb:.2f} MB")

    # Connect and show table statistics
    engine = create_engine(get_db_url())

    click.echo(click.style("\nTable Statistics:", fg="green", bold=True))

    tables = [
        "projects",
        "runs",
        "configs",
        "metrics",
        "files",
        "custom_views",
        "dashboards",
    ]

    try:
        with engine.connect() as conn:
            for table in tables:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                click.echo(f"  {table:15s}: {count:>8,} rows")
    except Exception as e:
        click.echo(click.style(f"\nError reading database: {e}", fg="red"), err=True)


@db.command()
@click.option(
    "--sqlite-path",
    default=None,
    help="Path to SQLite database (default: ~/.trackai/trackai.db)",
)
@click.option(
    "--duckdb-path",
    default=None,
    help="Path to DuckDB database (default: from config)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def migrate(sqlite_path, duckdb_path, yes):
    """Migrate data from SQLite to DuckDB."""
    # Auto-detect SQLite path if not provided
    if sqlite_path is None:
        sqlite_path = check_sqlite_exists()
        if sqlite_path is None:
            click.echo(
                click.style(
                    "No SQLite database found at ~/.trackai/trackai.db",
                    fg="yellow",
                )
            )
            click.echo("Specify a custom path with --sqlite-path")
            sys.exit(1)

    # Use config path if not provided
    if duckdb_path is None:
        config = load_config()
        duckdb_path = (
            config.database.db_path
            if config.database.storage_type == "local"
            else config.database.local_cache_path
        )

    click.echo(click.style("Migrating SQLite to DuckDB", fg="blue", bold=True))
    click.echo(f"\nSource (SQLite): {sqlite_path}")
    click.echo(f"Destination (DuckDB): {duckdb_path}\n")

    # Confirm
    if not yes and not click.confirm("Proceed with migration?"):
        click.echo("Migration cancelled")
        sys.exit(0)

    # Perform migration
    success = migrate_sqlite_to_duckdb(sqlite_path, duckdb_path)

    if success:
        click.echo(
            click.style("\n✓ Migration completed successfully!", fg="green", bold=True)
        )
        sys.exit(0)
    else:
        click.echo(click.style("\n✗ Migration failed!", fg="red", bold=True), err=True)
        sys.exit(1)


@db.command()
@click.option("--output", default=None, help="Output path for backup file")
def backup(output):
    """Create a backup of the database."""
    config = load_config()

    if config.database.storage_type == "local":
        source_path = Path(config.database.db_path).expanduser()
    else:
        source_path = Path(config.database.local_cache_path).expanduser()

    if not source_path.exists():
        click.echo(click.style("Database does not exist", fg="red"), err=True)
        sys.exit(1)

    # Generate backup path if not provided
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = str(source_path.parent / f"trackai-backup-{timestamp}.duckdb")

    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Creating backup: {output_path}")
    shutil.copy2(source_path, output_path)

    click.echo(click.style("✓ Backup created successfully!", fg="green"))


@db.command()
@click.confirmation_option(prompt="Are you sure you want to delete all data?")
def reset():
    """Delete the database (requires confirmation)."""
    config = load_config()

    if config.database.storage_type == "local":
        db_path = Path(config.database.db_path).expanduser()
    else:
        db_path = Path(config.database.local_cache_path).expanduser()

    if db_path.exists():
        db_path.unlink()
        click.echo(click.style("✓ Database deleted", fg="green"))
    else:
        click.echo(click.style("Database does not exist", fg="yellow"))


@db.command()
@click.option(
    "--direction",
    type=click.Choice(["upload", "download", "both"]),
    default="upload",
    help="Sync direction (default: upload)",
)
def sync(direction):
    """Sync local database to/from S3."""
    from trackai.s3.sync import sync_from_s3

    config = load_config()

    if config.database.storage_type != "s3":
        click.echo(
            click.style(
                "S3 storage not configured. Use 'trackai config s3' to configure.",
                fg="yellow",
            )
        )
        sys.exit(1)

    try:
        if direction in ["download", "both"]:
            click.echo("Downloading from S3...")
            sync_from_s3()
            click.echo(click.style("✓ Successfully downloaded from S3!", fg="green"))

        if direction in ["upload", "both"]:
            click.echo("Uploading to S3...")
            sync_to_s3()
            click.echo(click.style("✓ Successfully uploaded to S3!", fg="green"))

    except Exception as e:
        click.echo(click.style(f"✗ Sync failed: {e}", fg="red"), err=True)
        sys.exit(1)
