"""
MCP (Model Context Protocol) Server endpoints for LLM integration.
These endpoints provide tools for AI agents to interact with TrackAI.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ...db.connection import get_db
from ...db.schema import Project, Run, Metric
from ...services.logger import LoggingService

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class MCPResponse(BaseModel):
    """Standard MCP response wrapper"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class GetRunsForProjectRequest(BaseModel):
    project_id: int
    limit: Optional[int] = 100
    state: Optional[str] = None


class GetMetricsForRunRequest(BaseModel):
    run_id: int


class GetMetricValuesRequest(BaseModel):
    run_id: int
    metric_path: str
    limit: Optional[int] = 1000


class BulkLogRequest(BaseModel):
    project: str
    run_id: Optional[str] = None
    name: Optional[str] = None
    metrics: Dict[str, Any]
    step: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class GetProjectSummaryRequest(BaseModel):
    project_id: int


class GetRunSummaryRequest(BaseModel):
    run_id: int


# ============================================================================
# MCP Tool Endpoints
# ============================================================================

@router.post("/get_all_projects", response_model=MCPResponse)
async def get_all_projects(db: Session = Depends(get_db)):
    """
    Get all projects in the system.

    Returns a list of projects with their metadata and run counts.
    """
    try:
        from sqlalchemy import func

        projects_query = db.query(
            Project,
            func.count(Run.id).label("total_runs")
        ).outerjoin(Run).group_by(Project.id)

        projects = projects_query.all()

        result = []
        for project, total_runs in projects:
            result.append({
                "id": project.id,
                "name": project.name,
                "project_id": project.project_id,
                "total_runs": total_runs or 0,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            })

        return MCPResponse(success=True, data=result)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/get_runs_for_project", response_model=MCPResponse)
async def get_runs_for_project(
    request: GetRunsForProjectRequest,
    db: Session = Depends(get_db)
):
    """
    Get all runs for a specific project.

    Args:
        project_id: The ID of the project
        limit: Maximum number of runs to return (default: 100)
        state: Filter by run state (running, completed, failed)
    """
    try:
        query = db.query(Run).filter(Run.project_id == request.project_id)

        if request.state:
            query = query.filter(Run.state == request.state)

        query = query.order_by(Run.created_at.desc()).limit(request.limit)
        runs = query.all()

        result = []
        for run in runs:
            result.append({
                "id": run.id,
                "run_id": run.run_id,
                "name": run.name,
                "state": run.state,
                "group_name": run.group_name,
                "created_at": run.created_at.isoformat(),
                "updated_at": run.updated_at.isoformat(),
            })

        return MCPResponse(success=True, data=result)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/get_metrics_for_run", response_model=MCPResponse)
async def get_metrics_for_run(
    request: GetMetricsForRunRequest,
    db: Session = Depends(get_db)
):
    """
    Get all unique metric names for a specific run.

    Args:
        run_id: The ID of the run
    """
    try:
        metrics = db.query(Metric.attribute_path).filter(
            Metric.run_id == request.run_id
        ).distinct().all()

        metric_names = [m[0] for m in metrics]

        return MCPResponse(success=True, data=metric_names)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/get_metric_values", response_model=MCPResponse)
async def get_metric_values(
    request: GetMetricValuesRequest,
    db: Session = Depends(get_db)
):
    """
    Get values for a specific metric across all steps.

    Args:
        run_id: The ID of the run
        metric_path: The path/name of the metric
        limit: Maximum number of values to return (default: 1000)
    """
    try:
        metrics_query = db.query(Metric).filter(
            Metric.run_id == request.run_id,
            Metric.attribute_path == request.metric_path
        ).order_by(Metric.step).limit(request.limit)

        metrics = metrics_query.all()

        result = []
        for metric in metrics:
            # Determine the value based on type
            value = None
            if metric.attribute_type == "float":
                value = metric.float_value
            elif metric.attribute_type == "int":
                value = metric.int_value
            elif metric.attribute_type == "string":
                value = metric.string_value
            elif metric.attribute_type == "bool":
                value = metric.bool_value

            result.append({
                "step": metric.step,
                "timestamp": metric.timestamp.isoformat() if metric.timestamp else None,
                "value": value,
                "type": metric.attribute_type,
            })

        return MCPResponse(success=True, data=result)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/get_project_summary", response_model=MCPResponse)
async def get_project_summary(
    request: GetProjectSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for a project.

    Args:
        project_id: The ID of the project
    """
    try:
        project = db.query(Project).filter(Project.id == request.project_id).first()
        if not project:
            return MCPResponse(success=False, error="Project not found")

        # Count runs by state
        running_runs = db.query(Run).filter(
            Run.project_id == request.project_id,
            Run.state == "running"
        ).count()

        completed_runs = db.query(Run).filter(
            Run.project_id == request.project_id,
            Run.state == "completed"
        ).count()

        failed_runs = db.query(Run).filter(
            Run.project_id == request.project_id,
            Run.state == "failed"
        ).count()

        total_runs = running_runs + completed_runs + failed_runs

        result = {
            "id": project.id,
            "name": project.name,
            "project_id": project.project_id,
            "total_runs": total_runs,
            "running_runs": running_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }

        return MCPResponse(success=True, data=result)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/get_run_summary", response_model=MCPResponse)
async def get_run_summary(
    request: GetRunSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Get summary for a specific run including latest metric values.

    Args:
        run_id: The ID of the run
    """
    try:
        run = db.query(Run).filter(Run.id == request.run_id).first()
        if not run:
            return MCPResponse(success=False, error="Run not found")

        # Get all metrics for this run (latest value for each metric)
        from sqlalchemy import func

        # Get latest metrics (where step is null or max step)
        subquery = db.query(
            Metric.attribute_path,
            func.max(Metric.step).label("max_step")
        ).filter(
            Metric.run_id == request.run_id
        ).group_by(Metric.attribute_path).subquery()

        metrics = db.query(Metric).join(
            subquery,
            (Metric.attribute_path == subquery.c.attribute_path) &
            ((Metric.step == subquery.c.max_step) | (subquery.c.max_step.is_(None)))
        ).filter(Metric.run_id == request.run_id).all()

        metrics_dict = {}
        for metric in metrics:
            value = None
            if metric.attribute_type == "float":
                value = metric.float_value
            elif metric.attribute_type == "int":
                value = metric.int_value
            elif metric.attribute_type == "string":
                value = metric.string_value
            elif metric.attribute_type == "bool":
                value = metric.bool_value

            metrics_dict[metric.attribute_path] = value

        result = {
            "id": run.id,
            "run_id": run.run_id,
            "name": run.name,
            "state": run.state,
            "group_name": run.group_name,
            "project_id": run.project_id,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
            "metrics": metrics_dict,
        }

        return MCPResponse(success=True, data=result)
    except Exception as e:
        return MCPResponse(success=False, error=str(e))


@router.post("/bulk_log", response_model=MCPResponse)
async def bulk_log(request: BulkLogRequest, db: Session = Depends(get_db)):
    """
    Log metrics for a run (create run if it doesn't exist).

    Args:
        project: Project name
        run_id: Optional run identifier (auto-generated if not provided)
        name: Optional run name
        metrics: Dictionary of metric_path: value
        step: Optional step number
        config: Optional configuration dictionary
    """
    try:
        service = LoggingService(db)

        # Get or create project
        from ...db.schema import Project
        project = db.query(Project).filter(Project.name == request.project).first()
        if not project:
            project = Project(name=request.project, project_id=f"{request.project}_auto")
            db.add(project)
            db.commit()
            db.refresh(project)

        # Get or create run
        if request.run_id:
            run = db.query(Run).filter(
                Run.project_id == project.id,
                Run.run_id == request.run_id
            ).first()
        else:
            run = None

        if not run:
            # Create new run
            import uuid
            run_id_str = request.run_id or f"run-{uuid.uuid4().hex[:8]}"
            run = Run(
                project_id=project.id,
                run_id=run_id_str,
                name=request.name or run_id_str,
                state="running"
            )
            db.add(run)
            db.commit()
            db.refresh(run)

        # Log metrics
        service.log_metrics(run.id, request.metrics, request.step)

        # Log config if provided
        if request.config:
            from ...db.schema import Config
            for key, value in request.config.items():
                import json
                config_entry = Config(
                    run_id=run.id,
                    key=key,
                    value=json.dumps(value)
                )
                db.add(config_entry)
            db.commit()

        return MCPResponse(
            success=True,
            data={
                "run_id": run.id,
                "run_identifier": run.run_id,
                "metrics_logged": len(request.metrics)
            }
        )
    except Exception as e:
        db.rollback()
        return MCPResponse(success=False, error=str(e))


@router.post("/upload_db_to_space", response_model=MCPResponse)
async def upload_db_to_space():
    """
    Upload database to Hugging Face Space (placeholder).
    This feature is deferred for future implementation.
    """
    return MCPResponse(
        success=False,
        error="Feature not yet implemented. Use local database storage."
    )


@router.post("/bulk_upload_media", response_model=MCPResponse)
async def bulk_upload_media():
    """
    Bulk upload media files (placeholder).
    This feature is deferred for future implementation.
    """
    return MCPResponse(
        success=False,
        error="Feature not yet implemented. Store file paths in metrics."
    )
