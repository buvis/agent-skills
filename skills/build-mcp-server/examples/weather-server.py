"""Weather MCP Server.

Wraps the OpenWeatherMap API as MCP tools for LLM consumption.
Demonstrates: simple GET endpoints, Pydantic response models, ToolAnnotations.
"""

import os
from typing import Annotated

import httpx
from pydantic import BaseModel, Field

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

# --- Configuration ---
BASE_URL = "https://api.openweathermap.org/data/2.5"
API_KEY = os.environ["OPENWEATHER_API_KEY"]


# --- Response Models ---


class CurrentWeather(BaseModel):
    """Current weather conditions for a location."""

    city: str = Field(description="City name.")
    temperature: float = Field(description="Temperature in Celsius.")
    feels_like: float = Field(description="Feels-like temperature in Celsius.")
    humidity: int = Field(description="Relative humidity percentage.")
    description: str = Field(description="Weather description (e.g., 'light rain').")
    wind_speed: float = Field(description="Wind speed in m/s.")


class ForecastDay(BaseModel):
    """One day in a weather forecast."""

    date: str = Field(description="Date in YYYY-MM-DD format.")
    temp_min: float = Field(description="Minimum temperature in Celsius.")
    temp_max: float = Field(description="Maximum temperature in Celsius.")
    description: str = Field(description="Weather description.")


# --- Server ---

mcp = MCPServer("weather")


# --- Tools ---


@mcp.tool(
    title="Get Current Weather",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def get_current_weather(
    city: Annotated[str, Field(description="City name (e.g., 'London', 'New York').")],
) -> CurrentWeather:
    """Get the current weather for a city."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/weather",
            params={"q": city, "appid": API_KEY, "units": "metric"},
        )
        response.raise_for_status()
        data = response.json()

    return CurrentWeather(
        city=data["name"],
        temperature=data["main"]["temp"],
        feels_like=data["main"]["feels_like"],
        humidity=data["main"]["humidity"],
        description=data["weather"][0]["description"],
        wind_speed=data["wind"]["speed"],
    )


@mcp.tool(
    title="Get Weather Forecast",
    annotations=ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=True,
    ),
)
async def get_forecast(
    city: Annotated[str, Field(description="City name.")],
    days: Annotated[int, Field(ge=1, le=5, description="Number of days (1-5).")] = 3,
) -> list[ForecastDay]:
    """Get a multi-day weather forecast for a city."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/forecast",
            params={"q": city, "appid": API_KEY, "units": "metric", "cnt": days * 8},
        )
        response.raise_for_status()
        data = response.json()

    # Group by date, take daily summary
    daily: dict[str, ForecastDay] = {}
    for item in data["list"]:
        date = item["dt_txt"].split(" ")[0]
        if date not in daily:
            daily[date] = ForecastDay(
                date=date,
                temp_min=item["main"]["temp_min"],
                temp_max=item["main"]["temp_max"],
                description=item["weather"][0]["description"],
            )
        else:
            daily[date].temp_min = min(daily[date].temp_min, item["main"]["temp_min"])
            daily[date].temp_max = max(daily[date].temp_max, item["main"]["temp_max"])

    return list(daily.values())[:days]
