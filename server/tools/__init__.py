from tools.registry import tool_registry
from tools.weather import WeatherTool

# manual registration — no decorators, no auto-discovery
tool_registry.register(WeatherTool())
