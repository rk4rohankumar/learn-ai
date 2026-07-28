import httpx

import config
from tools.base import Tool, ToolDefinition, ToolResult

API_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherTool(Tool):
    definition = ToolDefinition(
        name="weather",
        description="Get the current weather for a city.",
        input_schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city to get the weather for, e.g. 'Delhi' or 'Paris,FR'.",
                },
            },
            "required": ["city"],
        },
    )

    async def execute(self, arguments: dict) -> ToolResult:
        city = arguments.get("city")
        if not city:
            # business failure — bad input, execution itself is fine
            return ToolResult(
                success=False,
                content="Missing required argument: city",
            )

        # a network/HTTP-transport error raises out of here -> execution FAILED.
        # a "city not found" is a valid API answer -> business failure below.
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(
                API_URL,
                params={
                    "q": city,
                    "appid": config.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )

        if resp.status_code == 404:
            return ToolResult(
                success=False,
                content=f"City not found: {city}",
            )

        resp.raise_for_status()
        data = resp.json()

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]
        name = data.get("name", city)

        return ToolResult(
            success=True,
            content=f"Current weather in {name} is {temp}°C, {description}.",
            metadata={
                "city": name,
                "temp_c": temp,
                "description": description,
                "humidity": data["main"].get("humidity"),
            },
        )
