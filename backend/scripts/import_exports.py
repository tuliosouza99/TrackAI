"""
Import Neptune export data (parquet files) into TrackAI SQLite database.

This script imports experiment data from the exports/ directory:
- Parquet files containing metrics
- File metadata from files_list.json
- Configuration from log files
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import trackai
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trackai.db.schema import Base, Project, Run, Metric, Config, File
from trackai.db.connection import init_db, get_db_url


def extract_project_name(project_id: str) -> str:
    """
    Extract project name from project_id.

    Example: 'face-anti-spoofing_mestrado-tulio-285e678bb9252431' -> 'face-anti-spoofing'
    """
    parts = project_id.rsplit("_", 1)
    if len(parts) == 2:
        return parts[0].split("_")[0]
    return project_id


def import_parquet_files(
    parquet_dir: Path,
    db_session,
    project: Project,
    batch_size: int = 10000,
):
    """
    Import all parquet files for a project.

    Args:
        parquet_dir: Directory containing parquet files
        db_session: Database session
        project: Project object
        batch_size: Number of rows to process at a time
    """
    parquet_files = list(parquet_dir.glob("*.parquet"))
    print(f"Found {len(parquet_files)} parquet files")

    run_id_map = {}  # Map (project_id, run_id) -> database run ID
    run_metadata = {}  # Map run_key -> {name, tags}

    # First pass: extract sys/name and sys/tags for all runs
    print("\nFirst pass: extracting run metadata (sys/name, sys/tags)...")
    for i, parquet_file in enumerate(parquet_files, 1):
        df = pd.read_parquet(parquet_file)

        # Extract sys/name values
        sys_name_df = df[df['attribute_path'] == 'sys/name']
        for _, row in sys_name_df.iterrows():
            run_key = (row["project_id"], row["run_id"])
            if run_key not in run_metadata:
                run_metadata[run_key] = {}
            run_metadata[run_key]['name'] = row['string_value']

        # Extract sys/tags values
        sys_tags_df = df[df['attribute_path'] == 'sys/tags']
        for _, row in sys_tags_df.iterrows():
            run_key = (row["project_id"], row["run_id"])
            if run_key not in run_metadata:
                run_metadata[run_key] = {}
            # Convert array to comma-separated string
            tags = row['string_set_value']
            if tags is not None and len(tags) > 0:
                run_metadata[run_key]['tags'] = ','.join(str(tag) for tag in tags)

    print(f"  Found metadata for {len(run_metadata)} runs")

    for i, parquet_file in enumerate(parquet_files, 1):
        print(f"\nProcessing {i}/{len(parquet_files)}: {parquet_file.name}")

        # Read parquet file
        df = pd.read_parquet(parquet_file)
        print(f"  Loaded {len(df)} rows")

        # Process in batches
        for batch_start in range(0, len(df), batch_size):
            batch_end = min(batch_start + batch_size, len(df))
            batch_df = df.iloc[batch_start:batch_end]

            for _, row in batch_df.iterrows():
                # Get or create run
                run_key = (row["project_id"], row["run_id"])
                if run_key not in run_id_map:
                    # Check if run already exists in DB
                    db_run = (
                        db_session.query(Run)
                        .filter(
                            Run.project_id == project.id,
                            Run.run_id == row["run_id"],
                        )
                        .first()
                    )

                    if not db_run:
                        # Get metadata for this run
                        metadata = run_metadata.get(run_key, {})
                        run_name = metadata.get('name', row["run_id"])
                        run_tags = metadata.get('tags')

                        # Create new run
                        db_run = Run(
                            project_id=project.id,
                            run_id=row["run_id"],
                            name=run_name,
                            tags=run_tags,
                            state="completed",  # Assume completed for imported data
                        )
                        db_session.add(db_run)
                        db_session.flush()  # Get the ID

                    run_id_map[run_key] = db_run.id

                # Helper function to convert values
                def convert_value(val):
                    if pd.isna(val):
                        return None
                    if isinstance(val, Decimal):
                        return float(val)
                    return val

                # Create metric
                metric = Metric(
                    run_id=run_id_map[run_key],
                    attribute_path=row["attribute_path"],
                    attribute_type=row["attribute_type"],
                    step=convert_value(row["step"]),
                    timestamp=convert_value(row["timestamp"]),
                    float_value=convert_value(row["float_value"]),
                    int_value=convert_value(row["int_value"]),
                    string_value=convert_value(row["string_value"]),
                    bool_value=convert_value(row["bool_value"]),
                )
                db_session.add(metric)

            # Commit batch
            db_session.commit()
            print(f"  Processed rows {batch_start}-{batch_end}")


def import_file_metadata(files_dir: Path, db_session, project: Project):
    """
    Import file metadata from files_list.json files.

    Args:
        files_dir: Directory containing experiment files
        db_session: Database session
        project: Project object
    """
    project_dir = files_dir / project.project_id.replace("_", "/", 1)
    if not project_dir.exists():
        print(f"Files directory not found: {project_dir}")
        return

    # Find all run directories
    run_dirs = [d for d in project_dir.rglob("*") if d.is_dir() and d.name.startswith("MSC-")]

    print(f"Found {len(run_dirs)} run directories")

    for run_dir in run_dirs:
        run_id = run_dir.name

        # Get run from database
        db_run = (
            db_session.query(Run)
            .filter(Run.project_id == project.id, Run.run_id == run_id)
            .first()
        )

        if not db_run:
            print(f"  Warning: Run {run_id} not found in database, skipping")
            continue

        # Import files from different subdirectories
        for file_type in ["models", "predictions", "sample_batch"]:
            files_list_path = run_dir / file_type / "files_list.json"
            if files_list_path.exists():
                with open(files_list_path) as f:
                    files_data = json.load(f)

                for file_info in files_data:
                    db_file = File(
                        run_id=db_run.id,
                        file_type=file_type,
                        file_path=file_info.get("filePath", ""),
                        file_hash=file_info.get("fileHash"),
                        size=file_info.get("size"),
                        file_metadata=json.dumps(file_info.get("metadata", [])),
                    )
                    db_session.add(db_file)

        # Import source code metadata
        source_code_dir = run_dir / "source_code"
        if source_code_dir.exists():
            diff_file = source_code_dir / "diff"
            zip_file = source_code_dir / "files" / "files.zip"

            if diff_file.exists():
                db_file = File(
                    run_id=db_run.id,
                    file_type="source_code_diff",
                    file_path=str(diff_file.relative_to(files_dir)),
                    size=diff_file.stat().st_size,
                )
                db_session.add(db_file)

            if zip_file.exists():
                db_file = File(
                    run_id=db_run.id,
                    file_type="source_code_zip",
                    file_path=str(zip_file.relative_to(files_dir)),
                    size=zip_file.stat().st_size,
                )
                db_session.add(db_file)

    db_session.commit()
    print(f"Imported file metadata for {len(run_dirs)} runs")


def import_config_from_logs(files_dir: Path, db_session, project: Project):
    """
    Parse configuration from log files.

    Args:
        files_dir: Directory containing experiment files
        db_session: Database session
        project: Project object
    """
    project_dir = files_dir / project.project_id.replace("_", "/", 1)
    if not project_dir.exists():
        return

    run_dirs = [d for d in project_dir.rglob("*") if d.is_dir() and d.name.startswith("MSC-")]

    for run_dir in run_dirs:
        run_id = run_dir.name
        log_file = run_dir / "log"

        if not log_file.exists():
            continue

        # Get run from database
        db_run = (
            db_session.query(Run)
            .filter(Run.project_id == project.id, Run.run_id == run_id)
            .first()
        )

        if not db_run:
            continue

        # Parse config from log file
        try:
            with open(log_file) as f:
                content = f.read()

            # Extract config section (between ** Config ** markers)
            config_match = re.search(
                r"\*\*\s*Config\s*\*\*(.*?)(?=\n\n|\Z)",
                content,
                re.DOTALL | re.IGNORECASE,
            )

            if config_match:
                config_text = config_match.group(1)

                # Simple YAML-like parsing
                current_section = None
                config_dict = {}

                for line in config_text.split("\n"):
                    line = line.strip()
                    if not line:
                        continue

                    # Top-level section
                    if line.endswith(":") and not line.startswith(" "):
                        current_section = line[:-1]
                        config_dict[current_section] = {}
                    # Key-value pair
                    elif ":" in line and current_section:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()
                        config_dict[current_section][key] = value

                # Store config in database
                for key, value in config_dict.items():
                    db_config = Config(
                        run_id=db_run.id,
                        key=key,
                        value=json.dumps(value),
                    )
                    db_session.add(db_config)

        except Exception as e:
            print(f"  Warning: Failed to parse config for {run_id}: {e}")

    db_session.commit()


def main():
    """Main import function."""
    # Get exports directory
    repo_root = Path(__file__).parent.parent.parent
    exports_dir = repo_root / "exports"

    if not exports_dir.exists():
        print(f"Error: exports directory not found at {exports_dir}")
        return

    # Initialize database
    print("Initializing database...")
    init_db()

    # Create session
    engine = create_engine(get_db_url())
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Find all projects in exports/data
        data_dir = exports_dir / "data"
        files_dir = exports_dir / "files"

        if not data_dir.exists():
            print(f"Error: data directory not found at {data_dir}")
            return

        project_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
        print(f"Found {len(project_dirs)} projects")

        for project_dir in project_dirs:
            project_id = project_dir.name
            project_name = extract_project_name(project_id)

            print(f"\n{'='*60}")
            print(f"Importing project: {project_name} ({project_id})")
            print(f"{'='*60}")

            # Create or get project
            db_project = db.query(Project).filter(Project.project_id == project_id).first()
            if not db_project:
                db_project = Project(name=project_name, project_id=project_id)
                db.add(db_project)
                db.commit()
                db.refresh(db_project)
                print(f"Created project: {project_name}")
            else:
                print(f"Project already exists: {project_name}")

            # Import parquet files
            print("\n1. Importing metrics from parquet files...")
            import_parquet_files(project_dir, db, db_project)

            # Import file metadata
            print("\n2. Importing file metadata...")
            import_file_metadata(files_dir, db, db_project)

            # Import config from logs
            print("\n3. Importing configuration from logs...")
            import_config_from_logs(files_dir, db, db_project)

            print(f"\n✓ Completed import for {project_name}")

        print(f"\n{'='*60}")
        print("Import completed successfully!")
        print(f"{'='*60}")

        # Print summary
        total_projects = db.query(Project).count()
        total_runs = db.query(Run).count()
        total_metrics = db.query(Metric).count()

        print(f"\nDatabase summary:")
        print(f"  Projects: {total_projects}")
        print(f"  Runs: {total_runs}")
        print(f"  Metrics: {total_metrics}")

    except Exception as e:
        print(f"\nError during import: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
