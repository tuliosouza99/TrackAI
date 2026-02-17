"""API routes for projects."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from trackai.db.connection import get_db
from trackai.db.schema import Project, Run
from trackai.api.models import ProjectResponse, ProjectSummary, ProjectCreate

router = APIRouter()


@router.get("/", response_model=list[ProjectResponse])
def list_projects(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List all projects with pagination.

    Args:
        limit: Maximum number of projects to return
        offset: Number of projects to skip
        db: Database session

    Returns:
        List of projects
    """
    projects = db.query(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset).all()
    return projects


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get project details with summary statistics.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Project details with run statistics
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get run statistics
    total_runs = db.query(Run).filter(Run.project_id == project_id).count()
    running_runs = db.query(Run).filter(Run.project_id == project_id, Run.state == "running").count()
    completed_runs = db.query(Run).filter(Run.project_id == project_id, Run.state == "completed").count()
    failed_runs = db.query(Run).filter(Run.project_id == project_id, Run.state == "failed").count()

    return ProjectSummary(
        id=project.id,
        name=project.name,
        project_id=project.project_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        total_runs=total_runs,
        running_runs=running_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
    )


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.

    Args:
        project: Project data
        db: Database session

    Returns:
        Created project
    """
    # Check if project with same name or project_id already exists
    existing = (
        db.query(Project)
        .filter((Project.name == project.name) | (Project.project_id == project.project_id))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name or ID already exists")

    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and all associated runs.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Success message
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
