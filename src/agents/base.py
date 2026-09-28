from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract Base Class for all JARVIS Sub-Agents."""

    name: str = "BaseAgent"
    description: str = "Base agent representation"

    @abstractmethod
    async def process(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Processes an incoming prompt and yields a response."""
        pass
