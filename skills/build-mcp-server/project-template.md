# MCP Server Project Template

## Directory Structure

```text
<server-name>/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   ├── __init__.py
│   └── server.py
└── tests/
    ├── __init__.py
    └── test_server.py
```

## pyproject.toml

```toml
[project]
name = "<SERVER_NAME>"
version = "0.1.0"
description = "<ONE_LINE_DESCRIPTION>"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]==2.3.0",
    "httpx2==2.16.0",
    "pydantic>=2.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## src/__init__.py

```python
```

(Empty — just marks the directory as a package.)

## src/server.py — Skeleton

```python
"""<SERVER_NAME> MCP Server.

<DESCRIPTION>
"""

import os
from typing import Annotated

import httpx2
from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

# --- Configuration ---
BASE_URL = os.environ.get("<ENV_VAR_BASE_URL>", "<DEFAULT_URL>")
API_KEY = os.environ.get("<ENV_VAR_API_KEY>", "")

# --- Response Models ---

class ExampleResponse(BaseModel):
    """Response from the example endpoint."""
    id: str = Field(description="Unique identifier.")
    name: str = Field(description="Display name.")

# --- Server ---

mcp = MCPServer("<server-name>")

# --- Tools ---

@mcp.tool(
    title="Example Tool",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def example_tool(
    query: Annotated[str, Field(description="Search query.")],
    limit: Annotated[int, Field(ge=1, le=100, description="Maximum results.")] = 20,
) -> list[ExampleResponse]:
    """Search for examples matching the query."""
    async with httpx2.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/examples",
            params={"q": query, "limit": limit},
            headers={"Authorization": f"Bearer {API_KEY}"},
        )
        response.raise_for_status()
        data = response.json()
    return [ExampleResponse(**item) for item in data["results"]]
```

## tests/__init__.py

```python
```

## tests/test_server.py — Skeleton

The upstream API is faked with `httpx2.MockTransport`, and the server is called
through a real in-memory `Client(mcp)`. Fixture payloads are authored, not
captured from the real API.

```python
"""Tests for <SERVER_NAME> MCP Server."""

from unittest.mock import patch

import httpx2
import pytest

from mcp import Client

from src.server import mcp

REAL_CLIENT = httpx2.AsyncClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


def upstream(handler):
    """Patch httpx2.AsyncClient so every request is answered by handler."""
    def factory(*args, **kwargs):
        return REAL_CLIENT(*args, transport=httpx2.MockTransport(handler), **kwargs)
    return patch.object(httpx2, "AsyncClient", factory)


@pytest.mark.anyio
async def test_example_tool():
    """Success: structured results come back."""
    def handler(request):
        return httpx2.Response(200, json={"results": [{"id": "1", "name": "Test Item"}]})

    with upstream(handler):
        async with Client(mcp) as client:
            result = await client.call_tool("example_tool", {"query": "test"})
    assert not result.is_error
    assert result.structured_content["result"][0]["id"] == "1"


@pytest.mark.anyio
async def test_example_tool_passes_limit_upstream():
    """The limit argument reaches the upstream API."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json={"results": []})

    with upstream(handler):
        async with Client(mcp) as client:
            await client.call_tool("example_tool", {"query": "x", "limit": 5})
    assert seen[0].url.params["limit"] == "5"


@pytest.mark.anyio
async def test_example_tool_rejects_invalid_arguments():
    """Validation error: out-of-range input never reaches the upstream API."""
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json={"results": []})

    with upstream(handler):
        async with Client(mcp) as client:
            result = await client.call_tool("example_tool", {"query": "x", "limit": 1000})
    assert result.is_error
    assert seen == []


@pytest.mark.anyio
async def test_example_tool_reports_upstream_failure():
    """Upstream failure: an HTTP 500 surfaces as a tool error."""
    with upstream(lambda request: httpx2.Response(500, json={"error": "boom"})):
        async with Client(mcp) as client:
            result = await client.call_tool("example_tool", {"query": "x"})
    assert result.is_error
```

## .env.example

```bash
# <SERVER_NAME> Configuration
<ENV_VAR_BASE_URL>=https://api.example.com
<ENV_VAR_API_KEY>=your-api-key-here
```

## README.md Template

````markdown
# <SERVER_NAME> MCP Server

<DESCRIPTION>

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- API key from <SERVICE_NAME>

## Quick Start

```bash
# Install dependencies
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API credentials

# Run in development (opens MCP Inspector)
uv run mcp dev src/server.py

# Run for production (stdio transport)
uv run mcp run src/server.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `<ENV_VAR_BASE_URL>` | Yes | Base URL for the API |
| `<ENV_VAR_API_KEY>` | Yes | API authentication key |

## Tools

| Tool | Description | Read-only | Idempotent |
|------|-------------|-----------|------------|
| `example_tool` | Search for examples | ✅ | ✅ |

## Testing

```bash
uv run pytest
```

## Integration with MCP Hosts

### Claude Desktop (stdio)

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "uv",
      "args": ["--directory", "/path/to/<server-name>", "run", "mcp", "run", "src/server.py"],
      "env": {
        "<ENV_VAR_API_KEY>": "your-key"
      }
    }
  }
}
```

### Kiro CLI

Add to `.kiro/agents/<your-agent>.json`:

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "uv",
      "args": ["--directory", "/path/to/<server-name>", "run", "mcp", "run", "src/server.py"],
      "env": {
        "<ENV_VAR_API_KEY>": "${<ENV_VAR_API_KEY>}"
      }
    }
  }
}
```
````
