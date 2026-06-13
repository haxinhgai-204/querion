"""Observability service — track workflow runs and node-level steps."""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.run import Run, RunStep


async def create_run( # Hàm này nhận vào app_id, workflow_id, conversation_id và tạo ra một run
    db: AsyncSession,
    *,
    app_id: uuid.UUID | None = None,
    workflow_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
) -> Run:
    """Create a new run record when a workflow execution starts."""
    run = Run(
        app_id=app_id,
        workflow_id=workflow_id,
        conversation_id=conversation_id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()  # get the id without committing
    return run


async def log_step_start( # Hàm này nhận vào uuid của run, id và type của node, input của node
    db: AsyncSession,
    *,
    run_id: uuid.UUID,
    node_id: str,
    node_type: str,
    input_data: dict | None = None,
) -> RunStep:
    """Log the start of a node execution."""
    step = RunStep(
        run_id=run_id,
        node_id=node_id,
        node_type=node_type,
        started_at=datetime.now(timezone.utc),
        input_json=input_data,
    )
    db.add(step)
    await db.flush()
    return step


async def log_step_end( # Hàm này nhận vào step của node, output của node
    step: RunStep,
    *,
    output_data: dict | None = None,
) -> None:
    """Log the completion of a node execution."""
    step.ended_at = datetime.now(timezone.utc)
    step.output_json = output_data


async def complete_run(
    run: Run,
    *,
    status: str = "completed",
) -> None:
    """Mark a run as completed and calculate latency."""
    run.status = status
    run.ended_at = datetime.now(timezone.utc)
    if run.started_at:
        run.latency_ms = int((run.ended_at - run.started_at).total_seconds() * 1000)
