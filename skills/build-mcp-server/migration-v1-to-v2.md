# MCP Python SDK: v1 → v2 Migration Reference

> Source: https://py.sdk.modelcontextprotocol.io/migration/

## Suggested Migration Order

1. Update dependency pins (`mcp>=2,<3`)
2. Apply mechanical renames and import moves
3. Port server surface (FastMCP → MCPServer)
4. Port client code
5. Update transport setup
6. Run tests, fix validation errors
7. Address deprecation warnings

## Critical Renames (Every Project Hits These)

| v1 | v2 | First symptom |
|----|-----|---------------|
| `from mcp.server.fastmcp import FastMCP` | `from mcp.server import MCPServer` | `ModuleNotFoundError` |
| `tool.inputSchema` | `tool.input_schema` | `AttributeError` |
| `result.isError` | `result.is_error` | `AttributeError` |
| `result.nextCursor` | `result.next_cursor` | `AttributeError` |
| `result.structuredContent` | `result.structured_content` | `AttributeError` |
| `McpError` | `MCPError` | `ImportError` |
| `from mcp.types import Content` | `from mcp.types import ContentBlock` | `ImportError` |
| `httpx` | `httpx2` | `ModuleNotFoundError` |
| Resource URIs `AnyUrl` | `str` | `AttributeError` on `.host` |

## Server Migration (MCPServer)

### Constructor

```python
# v1
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Demo", "Instructions here")  # 2nd positional = instructions

# v2
from mcp.server import MCPServer
mcp = MCPServer("Demo", instructions="Instructions here")  # MUST be keyword
```

New positional order: `name, title, description, instructions, website_url, icons, version`

### Transport moved off constructor

```python
# v1
mcp = FastMCP("Demo", host="0.0.0.0", port=9000, stateless_http=True)
mcp.run(transport="streamable-http")

# v2
mcp = MCPServer("Demo")
mcp.run(transport="streamable-http", host="0.0.0.0", port=9000, stateless_http=True)
```

### Context injection (get_context removed)

```python
# v1
@mcp.tool()
async def my_tool(x: int) -> str:
    ctx = mcp.get_context()
    await ctx.report_progress(1, 2)
    return str(x)

# v2
from mcp.server.mcpserver import Context

@mcp.tool()
async def my_tool(x: int, ctx: Context) -> str:
    await ctx.report_progress(1, 2)
    return str(x)
```

### What is UNCHANGED on MCPServer

- `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()` — same arguments and signatures
- Tool return handling (CallToolResult passthrough, Image/Audio, model/dict/scalar wrapping)
- `list_tools()`, `list_resources()`, `add_tool()`, `add_resource()`
- Lifespan pattern
- `Image`, `Audio` helpers

## Dependencies Change

```toml
# v1
dependencies = ["mcp==1.28.1", "httpx>=0.27"]

# v2
dependencies = ["mcp==2.3.0", "httpx2==2.16.0"]  # httpx2 replaces httpx; needs Python 3.11+
```

New required deps: `opentelemetry-api>=1.28.0`, `mcp-types` (exact-pinned), `httpx2` (2.16.0 verified; `mcp` 2.3.0 requires `>=2.10.0`)
Removed: `httpx`, `httpx-sse`, `websockets`

## httpx → httpx2

```python
# v1
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get(url)

# v2
import httpx2
async with httpx2.AsyncClient() as client:
    resp = await client.get(url)
```

API is compatible — usually only the import name changes. Exception types also change (`httpx2.HTTPStatusError`, etc.).

## Testing

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

**Important**: `Client(server)` negotiates 2026-07-28 by default. For servers using `ctx.elicit()` or `ctx.session.create_message()`, use `Client(server, mode="legacy")`.

## Error Handling Changes

```python
# v1 — MCPError in @mcp.tool() → is_error=True tool result
# v2 — MCPError in @mcp.tool() → JSON-RPC protocol error (model doesn't see it!)

# For errors the model should see: raise any other exception
# For protocol-level rejection: raise MCPError

# v1 McpError constructor
raise McpError(ErrorData(code=INVALID_REQUEST, message="bad"))

# v2 MCPError constructor (direct args)
raise MCPError(INVALID_REQUEST, "bad")
```

## snake_case Field Renames (Common)

| v1 (camelCase) | v2 (snake_case) |
|----------------|-----------------|
| `inputSchema` | `input_schema` |
| `outputSchema` | `output_schema` |
| `isError` | `is_error` |
| `nextCursor` | `next_cursor` |
| `mimeType` | `mime_type` |
| `structuredContent` | `structured_content` |
| `serverInfo` | `server_info` |
| `protocolVersion` | `protocol_version` |
| `uriTemplate` | `uri_template` |
| `listChanged` | `list_changed` |
| `progressToken` | `progress_token` |

**Note**: Constructor kwargs accept BOTH spellings, but attribute access must use snake_case.
**Note**: `model_dump()` now produces snake_case. For wire format: `model_dump(by_alias=True, mode="json")`

## Deprecations (Still Works, Emits Warning)

- `ctx.info()`, `ctx.log()` (Logging) — use standard `logging` module
- `ctx.session.create_message()` (Sampling) — use `Resolve(Sample)`
- `ctx.session.list_roots()` (Roots) — use `Resolve(ListRoots)`
- `client.subscribe_resource()` — use `client.listen()` on 2026 connections

## 2026-07-28 Protocol Key Facts

- **No session**: stateless by default, any replica answers any request
- **No server→client requests**: `ctx.elicit()` raises `NoBackChannelError` on 2026 connections
- **Use resolvers**: `Resolve(fn)` works on both legacy and modern connections
- **WebSocket removed**: use Streamable HTTP
- **OpenTelemetry on by default**: every request gets `_meta: {}` envelope
