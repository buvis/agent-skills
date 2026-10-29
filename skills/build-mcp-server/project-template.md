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
requires-python = ">=3.10"
dependencies = [
    "mcp[cli]>=2.0.0,<3",
    "httpx>=0.28",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "anyio[trio]>=4.0",
    "pytest-anyio>=0.0.0",
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

import httpx
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
    async with httpx.AsyncClient() as client:
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

```python
"""Tests for <SERVER_NAME> MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp import Client

from src.server import mcp


@pytest.mark.anyio
async def test_example_tool():
    """Test example_tool returns structured results."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"id": "1", "name": "Test Item"}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("src.server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        async with Client(mcp) as client:
            result = await client.call_tool("example_tool", {"query": "test"})
            assert result.structured_content is not None
            assert result.structured_content["result"][0]["id"] == "1"


@pytest.mark.anyio
async def test_example_tool_with_limit():
    """Test example_tool respects limit parameter."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("src.server.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        async with Client(mcp) as client:
            result = await client.call_tool("example_tool", {"query": "x", "limit": 5})
            # Verify the limit was passed to the upstream API
            call_args = mock_client.get.call_args
            assert call_args[1]["params"]["limit"] == 5
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

- Python 3.10+
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
