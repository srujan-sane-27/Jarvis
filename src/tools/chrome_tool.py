import os
import subprocess
import asyncio
import logging
import re
import urllib.parse
from typing import Optional
import requests
from bs4 import BeautifulSoup
from src.tools.base import BaseTool

logger = logging.getLogger("jarvis.tools.chrome")


class ChromeTool(BaseTool):
    """Automates web navigation, Chrome browser launch, and content synthesis."""

    name = "chrome_controller"
    description = "Open websites in Google Chrome, browse YouTube/Google, or search the web."

    CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]

    SITE_PRESETS = {
        "youtube": "https://www.youtube.com",
        "yt": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "mail": "https://mail.google.com",
        "github": "https://github.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "linkedin": "https://www.linkedin.com",
        "instagram": "https://www.instagram.com",
        "chatgpt": "https://chatgpt.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "whatsapp": "https://web.whatsapp.com",
        "wikipedia": "https://www.wikipedia.org"
    }

    def __init__(self):
        self._chrome_path = self._detect_chrome()

    def _detect_chrome(self) -> Optional[str]:
        """Locates the Google Chrome binary on Windows."""
        for path in self.CHROME_PATHS:
            if os.path.exists(path):
                return path
        return None

    async def launch_chrome_url(self, url: str) -> str:
        """Launches target URL directly in Google Chrome (or system browser fallback)."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            if self._chrome_path and os.path.exists(self._chrome_path):
                subprocess.Popen([self._chrome_path, url])
                return f"Opening '{url}' in Google Chrome for you, Boss."
            else:
                import webbrowser
                await asyncio.to_thread(webbrowser.open, url)
                return f"Opening '{url}' in your default browser, Boss."
        except Exception as e:
            logger.error(f"Error launching Chrome for {url}: {e}")
            import webbrowser
            await asyncio.to_thread(webbrowser.open, url)
            return f"Opening '{url}' in browser, Boss."

    async def search_youtube(self, query: str) -> str:
        """Searches YouTube, extracts the top video, and plays it directly in Chrome with autoplay."""
        q = query.strip()
        encoded = urllib.parse.quote_plus(q)
        search_url = f"https://www.youtube.com/results?search_query={encoded}"

        target_url = search_url
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = await asyncio.to_thread(requests.get, search_url, headers=headers, timeout=5)
            matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", resp.text)
            if matches:
                video_id = matches[0]
                target_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        except Exception as e:
            logger.warning(f"Could not extract direct YouTube video ID: {e}")

        await self.launch_chrome_url(target_url)
        return f"Playing '{q}' directly on YouTube in Chrome for you, Boss."

    async def search_google(self, query: str) -> str:
        """Searches Google and opens the results directly in Chrome."""
        q = query.strip()
        encoded = urllib.parse.quote_plus(q)
        url = f"https://www.google.com/search?q={encoded}"
        await self.launch_chrome_url(url)
        return f"Searching Google for '{q}' in Google Chrome, Boss."

    async def open_target(self, target_text: str) -> str:
        """Intelligently routes site requests (e.g. YouTube, Reddit, custom URLs) to Chrome."""
        cleaned = target_text.lower().strip()

        # Check for search patterns: "youtube <query>" or "google <query>"
        if cleaned.startswith("youtube "):
            q = cleaned.replace("youtube ", "").strip()
            return await self.search_youtube(q)
        if cleaned.startswith("google "):
            q = cleaned.replace("google ", "").strip()
            return await self.search_google(q)

        # Check presets
        if cleaned in self.SITE_PRESETS:
            preset_url = self.SITE_PRESETS[cleaned]
            await self.launch_chrome_url(preset_url)
            return f"Opening {cleaned.capitalize()} in Google Chrome for you, Boss."

        # Check if it looks like a domain name
        if any(cleaned.endswith(tld) or (tld + "/") in cleaned for tld in [".com", ".org", ".net", ".io", ".co", ".in", ".edu", ".ai"]):
            await self.launch_chrome_url(cleaned)
            return f"Opening {cleaned} in Google Chrome for you, Boss."

        # Default: search Google for the target
        return await self.search_google(cleaned)

    async def open_url(self, url: str) -> str:
        """Lightweight text retrieval from a URL for background summarization."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else url

            paragraphs = [p.get_text().strip() for p in soup.find_all("p") if p.get_text().strip()]
            snippet = " ".join(paragraphs[:3])[:600]

            return f"Page Title: {title}\nURL: {url}\nContent Overview:\n{snippet}..."
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return f"Failed to retrieve {url}: {str(e)}"

    async def search_web(self, query: str) -> str:
        """Searches the web using DuckDuckGo HTML without requiring API keys."""
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

            return f"Queried web for '{query}'. Direct link: https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
        except Exception as e:
            logger.error(f"Search error for {query}: {e}")
            return f"Search encountered an issue: {str(e)}"


# Global singleton tool instance
chrome_tool = ChromeTool()
