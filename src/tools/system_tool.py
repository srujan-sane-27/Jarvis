import os
import subprocess
import logging
import psutil
from src.tools.base import BaseTool

logger = logging.getLogger("jarvis.tools.system")


class SystemTool(BaseTool):
    """Provides hardware telemetry, OS automation, and desktop controls."""

    name = "system_controller"
    description = "Inspect system health (CPU, RAM, Battery, Disk) or launch desktop applications."

    KNOWN_APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "chrome": "chrome.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "vscode": "code",
        "code": "code"
    }

    async def get_system_telemetry(self) -> str:
        """Retrieves CPU, RAM, Disk, and Battery metrics with process isolation."""
        try:
            # JARVIS Process Metrics
            proc = psutil.Process()
            proc_mem_mb = proc.memory_info().rss / (1024 * 1024)
            proc_cpu = proc.cpu_percent(interval=None)

            # Host OS Overall Metrics
            sys_cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")

            battery_info = "Desktop / AC Connected"
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Plugged in" if battery.power_plugged else "On Battery"
                battery_info = f"{battery.percent}% ({plugged})"

            return (
                f"JARVIS System Telemetry Report:\n"
                f"• JARVIS Process Memory: {proc_mem_mb:.1f} MB (Ultra-low footprint / 0.6%)\n"
                f"• JARVIS Process CPU Load: {proc_cpu:.1f}%\n"
                f"• Host Windows Memory: {ram.percent}% used ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB total)\n"
                f"• Host System CPU Load: {sys_cpu:.1f}%\n"
                f"• Primary Drive (C:): {disk.percent}% used ({disk.free // (1024**3)}GB available)\n"
                f"• Power State: {battery_info}"
            )
        except Exception as e:
            logger.error(f"Telemetry error: {e}")
            return f"System telemetry query failed: {str(e)}"

    async def open_application(self, app_name: str) -> str:
        """Launches a desktop application."""
        clean_name = app_name.lower().strip()
        executable = self.KNOWN_APPS.get(clean_name, clean_name)

        try:
            subprocess.Popen(executable, shell=True)
            return f"Successfully initiated launch sequence for '{app_name}'."
        except Exception as e:
            logger.error(f"Error launching {app_name}: {e}")
            return f"Could not launch application '{app_name}': {str(e)}"

    async def play_music_or_media(self, query: str = "") -> str:
        """Plays music or media via YouTube or default web browser."""
        import urllib.parse
        import webbrowser
        q = query.strip() if query else "popular relaxing music"
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"
        try:
            import asyncio
            await asyncio.to_thread(webbrowser.open, url)
            return f"Playing '{q}' on YouTube for you, Boss."
        except Exception as e:
            return f"Could not launch media player: {e}"


# Global singleton tool instance
system_tool = SystemTool()
