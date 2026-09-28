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
        """Retrieves CPU, RAM, Disk, and Battery metrics."""
        try:
            cpu_pct = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")

            battery_info = "N/A (Desktop / AC Power)"
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Plugged in" if battery.power_plugged else "On Battery"
                battery_info = f"{battery.percent}% ({plugged})"

            return (
                f"JARVIS System Telemetry:\n"
                f"• CPU Load: {cpu_pct}%\n"
                f"• Memory: {ram.percent}% used ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)\n"
                f"• Primary Disk: {disk.percent}% used ({disk.free // (1024**3)}GB free)\n"
                f"• Battery: {battery_info}"
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


# Global singleton tool instance
system_tool = SystemTool()
