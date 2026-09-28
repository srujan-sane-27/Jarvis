import asyncio
from src.tools.system_tool import system_tool
from src.tools.news_tool import news_tool


def test_system_telemetry():
    result = asyncio.run(system_tool.get_system_telemetry())
    assert "CPU Load" in result
    assert "Memory" in result
    print("Telemetry check passed.")


def test_weather_parsing():
    result = asyncio.run(news_tool.get_weather("London"))
    assert "Weather" in result or "Temperature" in result
    print("Weather check passed.")


if __name__ == "__main__":
    test_system_telemetry()
    test_weather_parsing()
    print("Tool tests passed successfully!")
