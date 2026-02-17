"""API routes for metrics."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from trackai.db.connection import get_db
from trackai.db.schema import Metric, Run
from trackai.api.models import MetricValue, MetricValuesResponse, MetricCompareRequest

router = APIRouter()


@router.get("/runs/{run_id}")
def list_metrics(run_id: int, db: Session = Depends(get_db)):
    """
    List all metric names for a run.

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        List of unique metric names
    """
    # Check if run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get distinct metric names
    metrics = (
        db.query(distinct(Metric.attribute_path))
        .filter(Metric.run_id == run_id)
        .order_by(Metric.attribute_path)
        .all()
    )

    return [m[0] for m in metrics]


@router.get("/runs/{run_id}/metric/{metric_path:path}", response_model=MetricValuesResponse)
def get_metric_values(
    run_id: int,
    metric_path: str,
    limit: int = 1000,
    offset: int = 0,
    step_min: Optional[int] = None,
    step_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get time-series values for a specific metric.

    Args:
        run_id: Run database ID
        metric_path: Metric attribute path (e.g., "train/loss")
        limit: Maximum number of values to return
        offset: Number of values to skip
        step_min: Minimum step number (inclusive)
        step_max: Maximum step number (inclusive)
        db: Database session

    Returns:
        Metric values with pagination info
    """
    # Check if run exists
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Build query
    query = db.query(Metric).filter(
        Metric.run_id == run_id,
        Metric.attribute_path == metric_path,
    )

    # Apply step filters
    if step_min is not None:
        query = query.filter(Metric.step >= step_min)
    if step_max is not None:
        query = query.filter(Metric.step <= step_max)

    # Get total count
    total = query.count()

    # Get values with pagination
    metrics = query.order_by(Metric.step).limit(limit).offset(offset).all()

    # Extract values based on type
    data = []
    for m in metrics:
        value = None
        if m.float_value is not None:
            value = m.float_value
        elif m.int_value is not None:
            value = m.int_value
        elif m.string_value is not None:
            value = m.string_value
        elif m.bool_value is not None:
            value = m.bool_value

        data.append(
            MetricValue(
                step=m.step,
                timestamp=m.timestamp,
                value=value,
            )
        )

    has_more = (offset + limit) < total

    return MetricValuesResponse(data=data, has_more=has_more)


@router.post("/compare")
def compare_metrics(request: MetricCompareRequest, db: Session = Depends(get_db)):
    """
    Compare metrics across multiple runs.

    Args:
        request: Comparison request with run IDs and metric paths
        db: Database session

    Returns:
        Nested dict: {run_id: {metric_path: [{step, value}]}}
    """
    result = {}

    for run_id in request.run_ids:
        # Check if run exists
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            continue

        result[run_id] = {}

        for metric_path in request.metric_paths:
            # Get all values for this metric
            metrics = (
                db.query(Metric)
                .filter(
                    Metric.run_id == run_id,
                    Metric.attribute_path == metric_path,
                )
                .order_by(Metric.step)
                .all()
            )

            # Extract values
            values = []
            for m in metrics:
                value = None
                if m.float_value is not None:
                    value = m.float_value
                elif m.int_value is not None:
                    value = m.int_value
                elif m.string_value is not None:
                    value = m.string_value
                elif m.bool_value is not None:
                    value = m.bool_value

                values.append({"step": m.step, "value": value})

            result[run_id][metric_path] = values

    return result
