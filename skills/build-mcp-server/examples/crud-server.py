"""Tasks API MCP Server.

Wraps a REST CRUD API (tasks/todos) as MCP tools.
Demonstrates: GET/POST/PUT/DELETE mapping, destructive_hint, idempotent_hint,
Pydantic models for both input and output, error handling.
"""

import os
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

# --- Configuration ---
BASE_URL = os.environ.get("TASKS_API_URL", "https://api.example.com/v1")
API_KEY = os.environ["TASKS_API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# --- Models ---


class Task(BaseModel):
    """A task/todo item."""

    id: str = Field(description="Unique task identifier.")
    title: str = Field(description="Task title.")
    description: str | None = Field(default=None, description="Detailed description.")
    status: Literal["todo", "in_progress", "done"] = Field(description="Current status.")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level.")
    assignee: str | None = Field(default=None, description="Assigned user.")


class TaskCreate(BaseModel):
    """Input for creating a new task."""

    title: Annotated[str, Field(max_length=200, description="Task title.")]
    description: str | None = Field(default=None, description="Detailed description.")
    priority: Literal["low", "medium", "high"] = Field(
        default="medium", description="Priority level."
    )
    assignee: str | None = Field(default=None, description="User to assign.")


class TaskUpdate(BaseModel):
    """Input for updating an existing task."""

    title: str | None = Field(default=None, max_length=200, description="New title.")
    description: str | None = Field(default=None, description="New description.")
    status: Literal["todo", "in_progress", "done"] | None = Field(
        default=None, description="New status."
    )
    priority: Literal["low", "medium", "high"] | None = Field(
        default=None, description="New priority."
    )
    assignee: str | None = Field(default=None, description="New assignee.")


class DeleteConfirmation(BaseModel):
    """Confirmation that a task was deleted."""

    id: str = Field(description="ID of the deleted task.")
    deleted: bool = Field(description="Whether deletion succeeded.")


# --- Server ---

mcp = MCPServer("tasks")


# --- Tools ---


@mcp.tool(
    title="List Tasks",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def list_tasks(
    status: Annotated[
        Literal["todo", "in_progress", "done"] | None,
        Field(description="Filter by status."),
    ] = None,
    assignee: Annotated[str | None, Field(description="Filter by assignee.")] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Max results.")] = 20,
) -> list[Task]:
    """List tasks with optional filters."""
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if assignee:
        params["assignee"] = assignee

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tasks", params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

    return [Task(**item) for item in data["tasks"]]


@mcp.tool(
    title="Get Task",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def get_task(
    task_id: Annotated[str, Field(description="The task ID to retrieve.")],
) -> Task:
    """Get a single task by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/tasks/{task_id}", headers=HEADERS)
        response.raise_for_status()
        return Task(**response.json())


@mcp.tool(
    title="Create Task",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=False,
        open_world_hint=False,
    ),
)
async def create_task(task: TaskCreate) -> Task:
    """Create a new task."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/tasks",
            json=task.model_dump(exclude_none=True),
            headers=HEADERS,
        )
        response.raise_for_status()
        return Task(**response.json())


@mcp.tool(
    title="Update Task",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def update_task(
    task_id: Annotated[str, Field(description="The task ID to update.")],
    updates: TaskUpdate = TaskUpdate(),
) -> Task:
    """Update an existing task. Only provided fields are changed."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{BASE_URL}/tasks/{task_id}",
            json=updates.model_dump(exclude_none=True),
            headers=HEADERS,
        )
        response.raise_for_status()
        return Task(**response.json())


@mcp.tool(
    title="Delete Task",
    annotations=ToolAnnotations(
        read_only_hint=False,
        destructive_hint=True,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def delete_task(
    task_id: Annotated[str, Field(description="The task ID to delete.")],
) -> DeleteConfirmation:
    """Permanently delete a task. This cannot be undone."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BASE_URL}/tasks/{task_id}", headers=HEADERS)
        response.raise_for_status()

    return DeleteConfirmation(id=task_id, deleted=True)
