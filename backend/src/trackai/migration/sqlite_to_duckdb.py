"""Migration script from SQLite to DuckDB."""

import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def _create_duckdb_schema(engine):
    """Create DuckDB schema using raw SQL (DuckDB has limited foreign key support)."""
    with engine.connect() as conn:
        # Projects table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY,
                name VARCHAR UNIQUE NOT NULL,
                project_id VARCHAR UNIQUE NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        )

        # Runs table (no CASCADE - not supported by DuckDB)
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                run_id VARCHAR NOT NULL,
                name VARCHAR,
                group_name VARCHAR,
                tags VARCHAR,
                state VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(project_id, run_id)
            )
        """)
        )

        # Configs table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                key VARCHAR NOT NULL,
                value VARCHAR,
                UNIQUE(run_id, key)
            )
        """)
        )

        # Metrics table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                attribute_path VARCHAR NOT NULL,
                attribute_type VARCHAR NOT NULL,
                step INTEGER,
                timestamp TIMESTAMP,
                float_value DOUBLE,
                int_value INTEGER,
                string_value VARCHAR,
                bool_value BOOLEAN
            )
        """)
        )

        # Files table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                run_id INTEGER NOT NULL,
                file_type VARCHAR NOT NULL,
                file_path VARCHAR,
                file_hash VARCHAR,
                size INTEGER,
                file_metadata VARCHAR
            )
        """)
        )

        # Custom views table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS custom_views (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                filters VARCHAR,
                columns VARCHAR,
                sort_by VARCHAR,
                created_at TIMESTAMP
            )
        """)
        )

        # Dashboards table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id INTEGER PRIMARY KEY,
                project_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                widgets VARCHAR,
                layout VARCHAR,
                created_at TIMESTAMP
            )
        """)
        )

        # Create indexes
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_runs_group_name ON runs(group_name)")
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state)"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_run_attr ON metrics(run_id, attribute_path)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_run_step ON metrics(run_id, step)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_attr_type ON metrics(attribute_type)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_files_run_type ON files(run_id, file_type)"
            )
        )

        conn.commit()


def migrate_sqlite_to_duckdb(sqlite_path: str, duckdb_path: str) -> bool:
    """
    Migrate SQLite database to DuckDB.

    Args:
        sqlite_path: Path to SQLite database file
        duckdb_path: Path to DuckDB database file

    Returns:
        True if successful, False otherwise
    """
    sqlite_path_obj = Path(sqlite_path).expanduser()
    duckdb_path_obj = Path(duckdb_path).expanduser()

    if not sqlite_path_obj.exists():
        print(f"Error: SQLite database not found at {sqlite_path}")
        return False

    # 1. Create backup
    backup_path = (
        sqlite_path_obj.parent
        / f"{sqlite_path_obj.stem}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}{sqlite_path_obj.suffix}"
    )
    shutil.copy2(sqlite_path_obj, backup_path)
    print(f"Created backup: {backup_path}")

    # 2. Connect to both databases
    sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
    duckdb_engine = create_engine(f"duckdb:///{duckdb_path}")

    print("Connected to both databases")

    # 3. Create schema in DuckDB using raw SQL (DuckDB-compatible)
    _create_duckdb_schema(duckdb_engine)
    print("Created DuckDB schema")

    # 4. Copy data table by table
    tables = [
        "projects",
        "runs",
        "configs",
        "metrics",
        "files",
        "custom_views",
        "dashboards",
    ]

    for table_name in tables:
        print(f"Migrating table: {table_name}...")
        rows_copied = _copy_table_data(sqlite_engine, duckdb_engine, table_name)
        print(f"  ✓ Copied {rows_copied} rows")

    # 5. Verify
    print("\nVerifying migration...")
    success = _verify_migration(sqlite_engine, duckdb_engine, tables)

    if success:
        print("\n✓ Migration completed successfully!")

        # Rename old SQLite file
        old_path = (
            sqlite_path_obj.parent
            / f"{sqlite_path_obj.stem}.old{sqlite_path_obj.suffix}"
        )
        shutil.move(sqlite_path_obj, old_path)
        print(f"Renamed old database to: {old_path}")
    else:
        print("\n✗ Migration verification failed!")
        print("Rolling back changes...")
        duckdb_path_obj.unlink(missing_ok=True)

    return success


def _copy_table_data(source_engine, dest_engine, table_name: str) -> int:
    """
    Copy all data from source table to destination table.

    Args:
        source_engine: Source database engine
        dest_engine: Destination database engine
        table_name: Name of table to copy

    Returns:
        Number of rows copied
    """
    # Create sessions
    SourceSession = sessionmaker(bind=source_engine)
    DestSession = sessionmaker(bind=dest_engine)

    source_session = SourceSession()
    dest_session = DestSession()

    try:
        # Read all rows from source
        result = source_session.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()

        if not rows:
            return 0

        # Get column names
        columns = result.keys()

        # Insert into destination in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]

            # Build insert statement
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # Convert rows to dictionaries
            batch_dicts = [dict(zip(columns, row)) for row in batch]

            # Execute batch insert
            dest_session.execute(text(insert_sql), batch_dicts)

        dest_session.commit()
        return len(rows)

    except Exception as e:
        dest_session.rollback()
        print(f"Error copying table {table_name}: {e}")
        raise
    finally:
        source_session.close()
        dest_session.close()


def _verify_migration(source_engine, dest_engine, tables: list[str]) -> bool:
    """
    Verify that migration was successful.

    Args:
        source_engine: Source database engine
        dest_engine: Destination database engine
        tables: List of table names to verify

    Returns:
        True if verification passed, False otherwise
    """
    all_passed = True

    for table_name in tables:
        with source_engine.connect() as source_conn:
            with dest_engine.connect() as dest_conn:
                source_count = source_conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                dest_count = dest_conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()

                if source_count != dest_count:
                    print(
                        f"  ✗ {table_name}: {source_count} rows in source, {dest_count} in destination"
                    )
                    all_passed = False
                else:
                    print(f"  ✓ {table_name}: {source_count} rows")

    return all_passed


def check_sqlite_exists() -> str | None:
    """
    Check if SQLite database exists at default location.

    Returns:
        Path to SQLite database if exists, None otherwise
    """
    default_path = Path.home() / ".trackai" / "trackai.db"
    if default_path.exists():
        return str(default_path)
    return None
