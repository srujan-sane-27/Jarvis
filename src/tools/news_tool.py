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
        """Fetches top breaking news headlines from RSS feeds."""
        feed_url = self.RSS_FEEDS.get(category.lower(), self.RSS_FEEDS["tech"])
        try:
            feed = feedparser.parse(feed_url)
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

    async def get_weather(self, city: str = "Mumbai") -> str:
        """Fetches real-time weather using wttr.in (100% free, no API key)."""
        try:
            url = f"https://wttr.in/{city}?format=j1"
            headers = {"User-Agent": "curl/7.68.0"}
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                current = data["current_condition"][0]
                temp_c = current["temp_C"]
                desc = current["weatherDesc"][0]["value"]
                humidity = current["humidity"]
                wind_speed = current["windspeedKmph"]

                return (
                    f"Current Weather in {city.capitalize()}:\n"
                    f"• Condition: {desc}\n"
                    f"• Temperature: {temp_c}°C\n"
                    f"• Humidity: {humidity}%\n"
                    f"• Wind Speed: {wind_speed} km/h"
                )
            return f"Could not retrieve weather for {city} (Status: {resp.status_code})."
        except Exception as e:
            logger.error(f"Weather error for {city}: {e}")
            return f"Weather report unavailable: {str(e)}"


# Global singleton tool instance
news_tool = NewsTool()
