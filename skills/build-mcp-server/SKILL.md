---
name: build-mcp-server
description: Use when creating, scaffolding, or upgrading Python MCP servers from API specs (OpenAPI, docs, URLs, descriptions) or migrating v1 servers to v2. Triggers on "build mcp server", "create mcp server", "scaffold mcp", "migrate mcp v1 to v2".
compatibility: "Portable; needs Python, uv, and the pinned MCP SDK. API access is caller-supplied."
---

# Build MCP Server

Generate complete MCP servers in Python from user-provided API specifications. Accepts OpenAPI/Swagger, plain-text docs, URLs, Jira tickets, or verbal descriptions. Produces a full project: `server.py` with Pydantic models and ToolAnnotations, `pyproject.toml`, tests using in-memory Client, README, and `.env.example`.

Also handles migration of existing v1 servers to v2.

## Dependencies

Python 3.11+, uv, the target API specification, and the pinned SDK stack
`mcp==2.3.0` with `httpx2==2.16.0` (v2 of the SDK depends on `httpx2`, not
`httpx`; `httpx2` itself needs Python 3.11+). Dependency templates and test
scaffolding are in `project-template.md`. If the API specification is
unavailable, request it rather than invent endpoints.

**Verified** with `mcp==2.3.0` in a throwaway environment: `MCPServer`,
`Client(mcp)`, `is_error`, `structured_content`, `LATEST_PROTOCOL_VERSION`
(2026-07-28), both examples, and the generated scaffold's tests (success,
validation error, upstream failure, with `httpx2.MockTransport` and authored
payloads), and a stdio `initialize` exchange through `mcp run`. **Unverified**:
HTTP transport options, `ctx.elicit()` and sampling behavior, the `mode="legacy"`
client, OAuth, and every v1-to-v2 claim in `migration-v1-to-v2.md` beyond the
renames above. Label anything outside the verified list as unverified in output.
Bump the pins deliberately: re-run `tests/test_examples_smoke.py` first.

## Trigger

User provides an API specification in any form:
- **OpenAPI/Swagger** JSON or YAML (preferred — richest metadata)
- **Plain-text API documentation** (endpoints, parameters, responses in prose)
- **A URL** to an API documentation page
- **A Jira ticket** describing what the MCP server should expose
- **A verbal description** of what tools the server should have

## Reference Files — MUST READ before generating

Before processing, load these skill reference files:

| File | Purpose |
|------|---------|
| `sdk-reference.md` | MCP Python SDK v2 patterns, decorators, structured output |
| `project-template.md` | pyproject.toml, directory structure, test setup, README template |
| `migration-v1-to-v2.md` | Complete v1→v2 migration (renames, patterns, breaking changes) |
| `examples/weather-server.py` | Simple GET API example |
| `examples/crud-server.py` | Full CRUD API example |

## Output Structure

```
<server-name>/
├── pyproject.toml              # uv-compatible, pinned mcp dependency
├── README.md                   # What it does, how to run, env vars, tools table
├── src/
│   ├── __init__.py
│   └── server.py               # The MCP server implementation
├── tests/
│   ├── __init__.py
│   └── test_server.py          # In-memory tests using Client(mcp)
└── .env.example                # Environment variables needed
```

## Workflow

### Step 1 — Parse the API Specification

From whatever input, extract:

| Field | Description |
|-------|-------------|
| **API name** | Short name (becomes `MCPServer("name")`) |
| **Base URL** | Upstream API's base URL |
| **Authentication** | API key, Bearer token, OAuth, none |
| **Endpoints** | Each: method, path, parameters, response shape |
| **Rate limits** | Any known rate limiting |

Present the extracted spec to the user for confirmation before generating.

### Step 2 — Map Endpoints to MCP Primitives

| API Pattern | MCP Primitive | Rationale |
|-------------|--------------|-----------|
| GET returning data | `@mcp.tool()` with `read_only_hint=True` | Model calls to get info |
| GET with path param (single item) | `@mcp.resource("uri://{id}")` | Addressable data |
| POST/PUT/DELETE (mutations) | `@mcp.tool()` with `destructive_hint=True` | Side effects |
| GET list (search/filter) | `@mcp.tool()` with `read_only_hint=True` | Filtered retrieval |
| Static reference data | `@mcp.resource("uri://...")` | Fixed read-only data |

Rules:
- **Prefer tools over resources** for anything needing parameters
- **Use resources** only for naturally addressable data that rarely changes
- **Every tool gets ToolAnnotations** — always set `read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint`
- **Group related endpoints** into one tool if they share params and model would naturally use them together

### Step 3 — Design Pydantic Models

For each tool:
1. **Input**: If >2 params, create `BaseModel` for request body
2. **Output**: Create `BaseModel` for response (enables `structured_content`)
3. **Descriptions**: Every field gets `Field(description=...)` via `Annotated`
4. **Constraints**: `ge`, `le`, `max_length`, `Literal` enums where API constrains
5. **Optional**: Match API's optional params with Python defaults

### Step 4 — Generate Server Code

```python
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

mcp = MCPServer("server-name")

@mcp.tool(
    title="Human-readable title",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    ),
)
async def tool_name(
    param: Annotated[str, Field(description="What this param is.")],
    optional_param: Annotated[int, Field(ge=1, le=100, description="Page size.")] = 20,
) -> ResponseModel:
    """Docstring becomes the tool description the model sees."""
    async with httpx2.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/endpoint", params={"q": param})
        response.raise_for_status()
        data = response.json()
    return ResponseModel(**data)
```

**Code requirements:**
- `httpx2` for all HTTP calls (async)
- Config from env vars (`os.environ["API_KEY"]`)
- All I/O tools must be `async def`
- Return Pydantic models — never raw dicts
- Let `raise_for_status()` propagate — SDK turns exceptions into `is_error=True` results the model can read
- No global state — stateless by design

### Step 5 — Generate Tests

Every tool gets an in-memory test:

```python
import httpx2
import pytest
from unittest.mock import patch
from mcp import Client
from src.server import mcp

REAL_CLIENT = httpx2.AsyncClient

@pytest.fixture
def anyio_backend():
    return "asyncio"

def upstream(handler):
    def factory(*args, **kwargs):
        return REAL_CLIENT(*args, transport=httpx2.MockTransport(handler), **kwargs)
    return patch.object(httpx2, "AsyncClient", factory)

@pytest.mark.anyio
async def test_tool_name():
    with upstream(lambda request: httpx2.Response(200, json={"key": "value"})):
        async with Client(mcp) as client:
            result = await client.call_tool("tool_name", {"param": "test"})
    assert not result.is_error
    assert result.structured_content is not None
```

Also test a validation error (out-of-range argument, upstream never called) and an
upstream failure (HTTP 500 gives `is_error`) per tool; see `project-template.md`.

### Step 6 — Generate Project Files

Use templates from `project-template.md`:
- `pyproject.toml`: `mcp[cli]==2.3.0`, `httpx2==2.16.0`, `pydantic>=2.12`, dev deps
- `README.md`: description, prerequisites, quick start, env vars table, tools table, integration examples
- `.env.example`: all required env vars with placeholder values

### Step 7 — Verify

Before presenting:
1. All imports resolve (no missing packages)
2. All type annotations valid
3. Every tool has: docstring, type hints, ToolAnnotations, return type
4. Tests import correct server module
5. No hardcoded secrets — everything from env vars
6. Run `python -c "from src.server import mcp"` if possible to verify syntax

## Design Principles

1. **Stateless** — No sessions, no handshake (2026-07-28 protocol). Any replica answers any request.
2. **Type-safe** — Pydantic models for input AND output. SDK validates both directions.
3. **Descriptive** — Every tool, parameter, response field has a description. LLMs work better with context.
4. **Annotated** — ToolAnnotations on every tool. Clients use these for permission flows.
5. **Testable** — In-memory tests using `Client(mcp)`. No network, no subprocess.
6. **Minimal** — One file for simple APIs. No over-engineering. No frameworks beyond the SDK.
7. **Async** — All I/O tools `async def`. Plain `def` only for pure computation.

## Error Handling Strategy

```python
# DO: Let exceptions become tool errors the model can read
async def get_user(user_id: str) -> User:
    """Get a user by ID."""
    async with httpx2.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/users/{user_id}")
        response.raise_for_status()  # HTTPStatusError → is_error=True
        return User(**response.json())

# DON'T: Return error strings or swallow exceptions
```

SDK catches exceptions and returns `is_error=True` with the message. Model reads it and can retry. Only raise `MCPError` for protocol-level failures.

## Authentication Patterns

```python
import os

# Pattern 1: API Key in header
HEADERS = {"Authorization": f"Bearer {os.environ['API_KEY']}"}

# Pattern 2: API Key as query param
PARAMS = {"api_key": os.environ["API_KEY"]}

# Pattern 3: Basic auth
AUTH = (os.environ["API_USER"], os.environ["API_PASS"])
```

Always document required env vars in `.env.example` and README.

## Migration Mode: v1 → v2

When user provides an existing v1 server for migration:

### Step 1 — Analyze v1 Server

Identify: import style, transport config, context usage, HTTP client, camelCase fields, error handling, testing patterns, elicitation/sampling usage.

### Step 2 — Apply Mechanical Renames

| v1 | v2 |
|----|-----|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` |
| `FastMCP("Name", "Instructions")` | `MCPServer("Name", instructions="Instructions")` |
| `McpError` | `MCPError` |
| `Content` | `ContentBlock` |
| `httpx` | `httpx2` (the SDK depends on it; Python 3.11+) |
| `.inputSchema` | `.input_schema` |
| `.isError` | `.is_error` |
| `.nextCursor` | `.next_cursor` |
| `.structuredContent` | `.structured_content` |
| `.mimeType` | `.mime_type` |

### Step 3 — Move Transport Config

```python
# v1: transport in constructor
mcp = FastMCP("Demo", host="0.0.0.0", port=9000)

# v2: transport at run() time
mcp = MCPServer("Demo")
mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)
```

### Step 4 — Fix Context Usage

```python
# v1
ctx = mcp.get_context()

# v2 — inject as parameter
from mcp.server.mcpserver import Context

@mcp.tool()
async def my_tool(x: int, ctx: Context) -> str:
    ...
```

### Step 5 — Fix HTTP Client

```python
# v1: import httpx
# v2: import httpx2  (separate package; the SDK depends on it, Python 3.11+)
```

### Step 6 — Fix Tests

```python
# v1
from mcp.shared.memory import create_connected_server_and_client_session
async with create_connected_server_and_client_session(server) as session:
    result = await session.call_tool("my_tool", {"x": 1})

# v2
from mcp import Client
async with Client(mcp) as client:
    result = await client.call_tool("my_tool", {"x": 1})
```

### Step 7 — Add v2 Enhancements

After mechanical migration:
- Add `ToolAnnotations` to every tool
- Add return type annotations for structured output
- Add `Field(description=...)` to parameters
- Update pyproject.toml: `mcp[cli]==2.3.0`, `httpx2==2.16.0`, `requires-python = ">=3.11"`
- Remove deprecated features (logging, sampling push calls)

### Step 8 — Verify

- All imports resolve
- `model_dump(by_alias=True)` where wire format needed
- No `AnyUrl` in resource URIs (use plain `str`)
- Tests use `Client(mcp)` pattern
- No `get_context()` calls remain
