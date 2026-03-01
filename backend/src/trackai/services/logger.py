"""Logging service for database operations."""

import hashlib
import json
import time
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from trackai.db.connection import get_session
from trackai.db.schema import Config, Metric, Project, Run


class LoggingService:
    """Service for logging experiment data to the database."""

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize logging service.

        Args:
            db_session: Optional database session. If not provided, creates a new one.
        """
        self.db = db_session or get_session()
        self._should_close_session = db_session is None

    def close(self):
        """Close the database session if it was created by this service."""
        if self._should_close_session and self.db:
            self.db.close()

    def get_or_create_project(self, project_name: str) -> Project:
        """
        Get existing project or create a new one.

        Args:
            project_name: Name of the project

        Returns:
            Project object
        """
        # Check if project exists
        project = self.db.query(Project).filter(Project.name == project_name).first()

        if not project:
            # Create new project with a generated project_id
            project_id = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            project = Project(name=project_name, project_id=project_id)
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)

        return project

    def create_run(
        self,
        project_name: str,
        run_name: Optional[str] = None,
        group: Optional[str] = None,
        config: Optional[dict] = None,
        resume: str = "never",
    ) -> Run:
        """
        Create a new run or resume an existing one.

        Args:
            project_name: Name of the project
            run_name: Optional name for the run (auto-generated if not provided)
            group: Optional group name for organizing runs
            config: Optional configuration dictionary
            resume: Resume mode ("never", "allow", "must")

        Returns:
            Run object
        """
        project = self.get_or_create_project(project_name)

        # Generate run name if not provided
        if not run_name:
            run_count = self.db.query(Run).filter(Run.project_id == project.id).count()
            run_name = f"run-{run_count + 1}"

        # Check if run exists
        existing_run = (
            self.db.query(Run)
            .filter(Run.project_id == project.id, Run.run_id == run_name)
            .first()
        )

        if existing_run:
            if resume == "never":
                raise ValueError(
                    f"Run '{run_name}' already exists in project '{project_name}'. "
                    f"Use resume='allow' or resume='must' to resume it."
                )
            # Resume existing run
            existing_run.state = "running"
            existing_run.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_run)
            return existing_run
        else:
            if resume == "must":
                raise ValueError(
                    f"Run '{run_name}' does not exist in project '{project_name}'. "
                    f"Cannot resume non-existent run."
                )

        # Create new run
        run = Run(
            project_id=project.id,
            run_id=run_name,
            name=run_name,
            group_name=group,
            state="running",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        # Store config if provided
        if config:
            self._log_config(run.id, config)

        return run

    def _log_config(self, run_id: int, config: dict, prefix: str = ""):
        """
        Recursively log configuration as flat key-value pairs.

        Args:
            run_id: Run database ID
            config: Configuration dictionary
            prefix: Key prefix for nested dicts
        """
        for key, value in config.items():
            full_key = f"{prefix}{key}" if prefix else key

            if isinstance(value, dict):
                # Recursively handle nested dicts
                self._log_config(run_id, value, prefix=f"{full_key}/")
            else:
                # Store as JSON
                config_entry = Config(
                    run_id=run_id, key=full_key, value=json.dumps(value)
                )
                self.db.add(config_entry)

        self.db.commit()

    def log_metrics(
        self,
        run_id: int,
        metrics: dict[str, Any],
        step: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Log metrics for a run.

        Args:
            run_id: Run database ID
            metrics: Dictionary of metric name -> value
            step: Optional step number
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        for metric_path, value in metrics.items():
            # Determine metric type and appropriate column
            if isinstance(value, bool):
                metric = Metric(
                    run_id=run_id,
                    attribute_path=metric_path,
                    attribute_type="bool",
                    step=step,
                    timestamp=timestamp,
                    bool_value=value,
                )
            elif isinstance(value, int):
                metric = Metric(
                    run_id=run_id,
                    attribute_path=metric_path,
                    attribute_type="int",
                    step=step,
                    timestamp=timestamp,
                    int_value=value,
                )
            elif isinstance(value, float):
                metric = Metric(
                    run_id=run_id,
                    attribute_path=metric_path,
                    attribute_type="float",
                    step=step,
                    timestamp=timestamp,
                    float_value=value,
                )
            elif isinstance(value, str):
                metric = Metric(
                    run_id=run_id,
                    attribute_path=metric_path,
                    attribute_type="string",
                    step=step,
                    timestamp=timestamp,
                    string_value=value,
                )
            else:
                # Convert other types to string
                metric = Metric(
                    run_id=run_id,
                    attribute_path=metric_path,
                    attribute_type="string",
                    step=step,
                    timestamp=timestamp,
                    string_value=str(value),
                )

            self.db.add(metric)

        self.db.commit()

        # Update run's updated_at timestamp
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.updated_at = datetime.utcnow()
            self.db.commit()

    def finish_run(self, run_id: int):
        """
        Mark a run as completed.

        Args:
            run_id: Run database ID
        """
        run = self.db.query(Run).filter(Run.id == run_id).first()
        if run:
            run.state = "completed"
            run.updated_at = datetime.utcnow()
            self.db.commit()
