"""Run class for experiment tracking."""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from trackai.config import load_config
from trackai.db.connection import init_db
from trackai.db.schema import Run as DBRun
from trackai.s3.sync import sync_from_s3, sync_to_s3
from trackai.services.logger import LoggingService


class Run:
    """
    Run object for tracking experiments.

    Compatible with trackio.Run API.
    """

    def __init__(
        self,
        project: str,
        name: Optional[str] = None,
        group: Optional[str] = None,
        config: Optional[dict] = None,
        resume: str = "never",
        **kwargs,
    ):
        """
        Initialize a run.

        Args:
            project: Project name
            name: Optional run name (auto-generated if not provided)
            group: Optional group name for organizing runs
            config: Optional configuration dictionary
            resume: Resume mode ("never", "allow", "must")
            **kwargs: Additional arguments (for compatibility)
        """
        self.project_name = project
        self.run_name = name
        self.group_name = group
        self.config = config or {}
        self._step_counter = 0
        self._temp_db_path = None

        # Handle S3 download for logging mode
        db_config = load_config()
        if db_config.database.storage_type == "s3":
            # In logging mode, download DB from S3 to temp location
            self._temp_db_path = Path(tempfile.mkdtemp()) / "trackai.duckdb"
            print("Downloading database from S3...")
            try:
                sync_from_s3(destination=self._temp_db_path)
                print(f"✓ Downloaded database to {self._temp_db_path}")
            except Exception as e:
                print(f"Note: Could not download from S3: {e}")
                print("Starting with empty database")

            # Override db connection to use temp file
            os.environ["TRACKAI_DB_PATH"] = str(self._temp_db_path)

            # Initialize database with temp path
            init_db(str(self._temp_db_path))

        # Initialize logging service
        self._logger = LoggingService()

        # Create run in database
        self._db_run = self._logger.create_run(
            project_name=project,
            run_name=name,
            group=group,
            config=config,
            resume=resume,
        )

        # Update run_name to actual name (in case it was auto-generated)
        self.run_name = self._db_run.run_id
        self.run_id = self._db_run.id

    def log(self, metrics: dict[str, Any], step: Optional[int] = None):
        """
        Log metrics to the run.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number (auto-incremented if not provided)
        """
        if step is None:
            step = self._step_counter
            self._step_counter += 1

        self._logger.log_metrics(
            run_id=self.run_id,
            metrics=metrics,
            step=step,
            timestamp=datetime.utcnow(),
        )

    def log_system(self, metrics: dict[str, Any]):
        """
        Log system metrics (GPU, etc.) without a step number.

        These metrics use timestamps for the x-axis instead of steps.

        Args:
            metrics: Dictionary of system metrics
        """
        self._logger.log_metrics(
            run_id=self.run_id,
            metrics=metrics,
            step=None,  # System metrics don't have steps
            timestamp=datetime.utcnow(),
        )

    def finish(self):
        """Finish the run and mark it as completed."""
        self._logger.finish_run(self.run_id)
        self._logger.close()

        # Auto-sync to S3 if configured
        try:
            db_config = load_config()
            if db_config.database.storage_type == "s3" and self._temp_db_path:
                print("Uploading database to S3...")
                sync_to_s3(source=self._temp_db_path)
                print("✓ Uploaded to S3")

                # Cleanup temp file
                if self._temp_db_path.exists():
                    # Remove the temp directory and all its contents
                    shutil.rmtree(self._temp_db_path.parent, ignore_errors=True)
                    print("✓ Cleaned up temp files")
        except Exception as e:
            print(f"Warning: Failed to sync to S3: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically finish the run."""
        if exc_type is None:
            # No exception, mark as completed
            self.finish()
        else:
            # Exception occurred, mark as failed
            run = self._logger.db.query(DBRun).filter(DBRun.id == self.run_id).first()
            if run:
                run.state = "failed"
                self._logger.db.commit()
            self._logger.close()

            # Cleanup temp files even on failure
            db_config = load_config()
            if db_config.database.storage_type == "s3" and self._temp_db_path:
                if self._temp_db_path.exists():
                    shutil.rmtree(self._temp_db_path.parent, ignore_errors=True)
        return False

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.run_name}', id={self.run_id})"
