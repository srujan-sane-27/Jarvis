import asyncio
import logging
from typing import Optional
import urllib.parse
import requests
from bs4 import BeautifulSoup
from src.tools.base import BaseTool

logger = logging.getLogger("jarvis.tools.chrome")


class ChromeTool(BaseTool):
    """Automates web navigation, Chrome control, and web page content synthesis."""

    name = "chrome_controller"
    description = "Open websites, browse pages, or search the web."

    def __init__(self):
        self._browser = None

    async def open_url(self, url: str) -> str:
        """Opens a target URL in browser or retrieves page content."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            # First try lightweight fast fetch
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else url

            # Extract first 500 characters of meaningful text
            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
            snippet = " ".join(paragraphs[:3])[:600]

            return f"Page Title: {title}\nURL: {url}\nContent Overview:\n{snippet}..."
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return f"Failed to retrieve {url}: {str(e)}"

    async def search_web(self, query: str) -> str:
        """Searches the web using DuckDuckGo HTML / instant API without requiring API keys."""
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            for result in soup.find_all("div", class_="result__body")[:4]:
                title_elem = result.find("a", class_="result__url")
                snippet_elem = result.find("a", class_="result__snippet")
                if title_elem and snippet_elem:
                    results.append(f"• {title_elem.get_text().strip()}\n  {snippet_elem.get_text().strip()}")

            if results:
                return f"Web Search Results for '{query}':\n\n" + "\n\n".join(results)

            # Fallback simple search
            return f"Queried web for '{query}'. Direct link: https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        except Exception as e:
            logger.error(f"Search error for {query}: {e}")
            return f"Search encountered an issue: {str(e)}"


# Global singleton tool instance
chrome_tool = ChromeTool()
