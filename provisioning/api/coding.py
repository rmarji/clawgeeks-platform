"""API endpoints for AI coding tasks powered by OpenHands."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import uuid

from ..services.openhands import OpenHandsService, get_openhands_service, DEVELOPER_AGENT


router = APIRouter(prefix="/coding", tags=["Coding Agent"])


# In-memory task storage (replace with Redis/DB in production)
_tasks: dict[str, dict] = {}


class CodingTaskRequest(BaseModel):
    """Request to run a coding task."""
    task: str
    workspace: Optional[str] = None
    model: Optional[str] = None


class CodingTaskResponse(BaseModel):
    """Response for a coding task."""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Status of a coding task."""
    task_id: str
    status: str  # pending, running, completed, error
    output: Optional[str] = None
    error: Optional[str] = None


@router.get("/status")
async def coding_status(service: OpenHandsService = Depends(get_openhands_service)):
    """Check if OpenHands coding service is available."""
    return {
        "available": service.is_available,
        "sdk_installed": service._sdk_available,
        "model": service.model,
        "developer_agent": DEVELOPER_AGENT
    }


@router.get("/agent")
async def get_developer_agent():
    """Get the Developer Agent archetype info."""
    return DEVELOPER_AGENT


@router.post("/task", response_model=CodingTaskResponse)
async def create_coding_task(
    request: CodingTaskRequest,
    background_tasks: BackgroundTasks,
    service: OpenHandsService = Depends(get_openhands_service)
):
    """
    Submit a coding task for the AI developer agent.
    
    The task runs asynchronously. Use GET /coding/task/{task_id} to check status.
    """
    if not service.is_available:
        raise HTTPException(
            status_code=503,
            detail="OpenHands service not available. Check SDK installation and API key."
        )
    
    task_id = str(uuid.uuid4())
    
    # Store task as pending
    _tasks[task_id] = {
        "status": "pending",
        "task": request.task,
        "workspace": request.workspace,
        "output": None,
        "error": None
    }
    
    # Run task in background
    async def run_task():
        _tasks[task_id]["status"] = "running"
        result = await service.run_task(
            task=request.task,
            workspace=request.workspace
        )
        _tasks[task_id].update(result)
    
    background_tasks.add_task(run_task)
    
    return CodingTaskResponse(
        task_id=task_id,
        status="pending",
        message=f"Task submitted. Poll GET /coding/task/{task_id} for status."
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of a coding task."""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = _tasks[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        output=task.get("output"),
        error=task.get("error")
    )


@router.get("/tasks")
async def list_tasks(limit: int = 10):
    """List recent coding tasks."""
    tasks = [
        {"task_id": tid, **task}
        for tid, task in list(_tasks.items())[-limit:]
    ]
    return {"tasks": tasks, "total": len(_tasks)}
