"""Smoke-test both example servers through a real in-memory MCP client.

Upstream HTTP is faked with httpx2.MockTransport; the payloads are authored
fixtures, not captured API responses. Needs the pinned SDK:

    uv run --with mcp==2.3.0 --with pytest pytest skills/build-mcp-server/tests

Without mcp installed the tests SKIP; a skip is not a pass.
"""

import asyncio
import importlib.util
import json
from pathlib import Path
import os
from unittest.mock import patch

import pytest

pytest.importorskip("mcp", reason="SKIPPED, NOT PASSED: install mcp==2.3.0 to run the examples")
httpx2 = pytest.importorskip("httpx2", reason="SKIPPED, NOT PASSED: install httpx2")

from mcp import Client  # noqa: E402

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
ENV = {"OPENWEATHER_API_KEY": "k", "TASKS_API_KEY": "k", "TASKS_API_URL": "https://api.invalid/v1"}
REAL_CLIENT = httpx2.AsyncClient


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), EXAMPLES / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, ENV):
        spec.loader.exec_module(module)
    return module


def call(module, tool, arguments, handler):
    """Call a tool through Client(server) with upstream answered by handler."""
    def factory(*args, **kwargs):
        return REAL_CLIENT(*args, transport=httpx2.MockTransport(handler), **kwargs)

    async def run():
        async with Client(module.mcp) as client:
            return await client.call_tool(tool, arguments)

    with patch.object(httpx2, "AsyncClient", factory):
        return asyncio.run(run())


def text(result):
    return " ".join(getattr(block, "text", "") for block in result.content)


WEATHER = {"name": "Testville", "main": {"temp": 12.5, "feels_like": 11.0, "humidity": 70},
           "weather": [{"description": "light rain"}], "wind": {"speed": 3.2}}
TASK = {"id": "t1", "title": "Write tests", "status": "todo", "priority": "medium"}


def test_weather_success():
    module = load("weather-server")
    result = call(module, "get_current_weather", {"city": "Testville"},
                  lambda request: httpx2.Response(200, json=WEATHER))
    assert not result.is_error
    assert "Testville" in text(result) and "light rain" in text(result)


def test_weather_validation_error_is_reported():
    module = load("weather-server")
    result = call(module, "get_forecast", {"city": "Testville", "days": 9},
                  lambda request: httpx2.Response(200, json={"list": []}))
    assert result.is_error


def test_weather_upstream_failure_is_reported():
    module = load("weather-server")
    result = call(module, "get_current_weather", {"city": "Nowhere"},
                  lambda request: httpx2.Response(404, json={"message": "city not found"}))
    assert result.is_error


def test_crud_get_task_success():
    module = load("crud-server")
    result = call(module, "get_task", {"task_id": "t1"},
                  lambda request: httpx2.Response(200, json=TASK))
    assert not result.is_error
    assert "Write tests" in text(result)


def test_crud_create_validation_error_never_reaches_upstream():
    module = load("crud-server")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(201, json=TASK)

    result = call(module, "create_task", {"task": {"title": "x" * 201}}, handler)
    assert result.is_error
    assert seen == []


def test_crud_delete_upstream_failure_is_reported():
    module = load("crud-server")
    result = call(module, "delete_task", {"task_id": "t1"},
                  lambda request: httpx2.Response(500, content=json.dumps({"error": "boom"})))
    assert result.is_error
