import asyncio
import logging
import requests
import feedparser
from src.tools.base import BaseTool

logger = logging.getLogger("jarvis.tools.news")


class NewsTool(BaseTool):
    """Provides real-time news headlines, tech intelligence, and live weather telemetry."""

    name = "news_and_intelligence"
    description = "Retrieve live breaking news, technology updates, or local weather conditions."

    RSS_FEEDS = {
        "tech": "https://feeds.feedburner.com/TechCrunch/",
        "general": "http://feeds.bbci.co.uk/news/rss.xml",
        "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"
    }

    async def get_top_news(self, category: str = "tech", limit: int = 4) -> str:
        """Fetches top breaking news headlines from RSS feeds non-blockingly."""
        feed_url = self.RSS_FEEDS.get(category.lower(), self.RSS_FEEDS["tech"])
        try:
            feed = await asyncio.to_thread(feedparser.parse, feed_url)
            if not feed.entries:
                return f"No news entries found for category '{category}'."

            items = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:120].strip()
                items.append(f"• {title}\n  {summary}...\n  Source: {link}")

            return f"Top {category.capitalize()} News Briefing:\n\n" + "\n\n".join(items)
        except Exception as e:
            logger.error(f"Error retrieving news: {e}")
            return f"Could not retrieve news headlines: {str(e)}"

    async def get_weather_data(self, city: str = "Mumbai") -> dict:
        """Fetches raw weather data non-blockingly."""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            headers = {"User-Agent": "curl/7.68.0"}
            resp = await asyncio.to_thread(requests.get, url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                return {
                    "success": True,
                    "city": city.capitalize(),
                    "temp_c": current.get("temp_C", "N/A"),
                    "desc": current["weatherDesc"][0]["value"] if current.get("weatherDesc") else "Clear",
                    "humidity": current.get("humidity", "N/A"),
                    "wind": current.get("windspeedKmph", "N/A")
                }
            return {"success": False, "error": f"Status {resp.status_code}"}
        except Exception as e:
            logger.error(f"Weather error for {city}: {e}")
            return {"success": False, "error": str(e)}

    async def get_weather(self, city: str = "Mumbai") -> str:
        """Fetches real-time weather using wttr.in (100% free, no API key)."""
        data = await self.get_weather_data(city)
        if data.get("success"):
            return (
                f"Current Weather in {data['city']}:\n"
                f"• Condition: {data['desc']}\n"
                f"• Temperature: {data['temp_c']}°C\n"
                f"• Humidity: {data['humidity']}%\n"
                f"• Wind Speed: {data['wind']} km/h"
            )
        return f"Weather report unavailable for {city}: {data.get('error')}"

    async def get_weather_voice(self, city: str = "Mumbai") -> str:
        """Returns spoken weather sentence."""
        data = await self.get_weather_data(city)
        if data.get("success"):
            return f"In {data['city']}, it is currently {data['temp_c']} degrees Celsius with {data['desc'].lower()}."
        return f"I could not retrieve the weather for {city} right now."


# Global singleton tool instance
news_tool = NewsTool()
