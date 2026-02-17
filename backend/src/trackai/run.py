"""Run class for experiment tracking."""

from datetime import datetime
from typing import Any, Optional

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

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically finish the run."""
        from trackai.db.schema import Run as DBRun

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
        return False

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.run_name}', id={self.run_id})"
