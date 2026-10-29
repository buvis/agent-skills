# MCP Python SDK v2 — Reference for Code Generation

> Source: https://py.sdk.modelcontextprotocol.io/ (2026-07-28 spec)

## Installation

```bash
uv add "mcp[cli]"
# or: pip install "mcp[cli]"
```

Requires Python 3.10+.

## Server Class

```python
from mcp.server import MCPServer

mcp = MCPServer("ServerName")
```

- Constructor takes: `name` (required), `instructions` (optional server-level description)
- Transport is configured at `run()` time, NOT in constructor
- `MCPServer` was renamed from `FastMCP` in v2

## Tools — `@mcp.tool()`

### Basic tool (sync, runs in thread)

```python
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

### Async tool (for I/O)

```python
@mcp.tool()
async def fetch_data(query: str) -> DataModel:
    """Fetch data from upstream API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/data", params={"q": query})
        resp.raise_for_status()
        return DataModel(**resp.json())
```

### With Field descriptions and constraints

```python
from typing import Annotated, Literal
from pydantic import Field

@mcp.tool()
async def search(
    query: Annotated[str, Field(description="Search term.")],
    limit: Annotated[int, Field(ge=1, le=100, description="Max results.")] = 20,
    sort: Literal["relevance", "date", "name"] | None = None,
) -> SearchResults:
    """Search the catalog."""
    ...
```

### With ToolAnnotations

```python
from mcp.types import ToolAnnotations

@mcp.tool(
    title="Search Catalog",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def search_catalog(query: str) -> list[Item]:
    """Search the product catalog."""
    ...
```

**ToolAnnotations fields:**
- `read_only_hint` (bool): tool does not modify anything
- `destructive_hint` (bool): tool may delete/destroy data (only meaningful if not read-only)
- `idempotent_hint` (bool): calling twice = calling once (safe to retry)
- `open_world_hint` (bool): tool accesses external/internet data vs. closed dataset

### Override name/description

```python
@mcp.tool(name="custom_name", description="Custom description overriding docstring.")
def my_func(x: int) -> int:
    return x * 2
```

## Structured Output

The **return type annotation** IS the output schema.

### Scalar returns (wrapped in `{"result": ...}`)

```python
@mcp.tool()
def count_items(category: str) -> int:
    """Count items in a category."""
    return 42
# structured_content = {"result": 42}
```

### Pydantic model returns (object, no wrapper)

```python
from pydantic import BaseModel, Field

class WeatherData(BaseModel):
    temperature: float = Field(description="Degrees Celsius.")
    humidity: float = Field(description="Relative humidity, 0-1.")
    conditions: str

@mcp.tool()
def get_weather(city: str) -> WeatherData:
    """Current weather for a city."""
    return WeatherData(temperature=16.2, humidity=0.83, conditions="Overcast")
# structured_content = {"temperature": 16.2, "humidity": 0.83, "conditions": "Overcast"}
```

### List returns (wrapped in `{"result": [...]}`)

```python
@mcp.tool()
def list_users(role: str) -> list[User]:
    """List users by role."""
    return [User(name="Alice"), User(name="Bob")]
# structured_content = {"result": [{"name": "Alice"}, {"name": "Bob"}]}
```

### dict[str, T] returns (object, no wrapper)

```python
@mcp.tool()
def get_scores(team: str) -> dict[str, int]:
    """Get player scores."""
    return {"alice": 10, "bob": 8}
# structured_content = {"alice": 10, "bob": 8}
```

### TypedDict (same as BaseModel, no wrapper)

```python
from typing import TypedDict

class Stats(TypedDict):
    count: int
    avg: float

@mcp.tool()
def get_stats() -> Stats:
    """Get stats."""
    return Stats(count=10, avg=3.5)
```

### Opt out of structured output

```python
@mcp.tool(structured_output=False)
def narrative_report(topic: str) -> str:
    """Generate a human-readable report."""
    return "A long narrative..."
```

## Resources — `@mcp.resource()`

```python
@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"
```

- URI template uses `{param}` for path parameters
- Used for addressable, read-only data
- Less common than tools for API wrappers

## Error Handling

```python
# Exceptions raised → is_error=True tool result (model reads the message)
@mcp.tool()
async def get_user(user_id: str) -> User:
    """Get user by ID."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/users/{user_id}")
        resp.raise_for_status()  # HTTPStatusError → model sees "404 Not Found" etc.
        return User(**resp.json())

# MCPError → protocol-level error (model doesn't see it, use sparingly)
from mcp import MCPError
from mcp.types import INVALID_PARAMS
raise MCPError(INVALID_PARAMS, "That operation is not supported")
```

## Testing (in-memory)

```python
import pytest
from mcp import Client
from src.server import mcp

@pytest.mark.anyio
async def test_add():
    async with Client(mcp) as client:
        result = await client.call_tool("add", {"a": 1, "b": 2})
        assert result.structured_content == {"result": 3}
```

- `Client(mcp)` connects in-memory — no transport, no subprocess
- Use `pytest-anyio` for async test support
- Mock upstream HTTP calls with `unittest.mock.patch`

## Running

```bash
# Development (opens MCP Inspector)
uv run mcp dev src/server.py

# Production (stdio — for local MCP hosts like Claude Desktop)
uv run mcp run src/server.py

# Production (HTTP — for remote/scaled deployments)
# In code: mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

## Key Protocol Facts (2026-07-28)

- **Stateless**: No handshake, no session. Every request carries its own metadata.
- **No server→client calls**: Server cannot push to client. Use `Resolve()` for user input.
- **Both eras served**: Same server answers 2025-era clients (with session) and 2026-era clients (stateless).
- **Validation**: SDK validates both input args and output against schemas.
- **snake_case**: All Python attributes are snake_case (wire is still camelCase).
