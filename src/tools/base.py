import functools
import logging
from typing import Dict, Any, Callable, Optional
from src.security.auth import security_manager

logger = logging.getLogger("jarvis.tools.base")


def require_authorization(func: Callable):
    """Decorator ensuring high-privilege actions are gated by security authorization."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not security_manager.is_session_active():
            logger.warning(f"Unauthorized attempt to execute {func.__name__}")
            return (
                "ACTION_DENIED: High-privilege command requires voice authorization. "
                "Please speak your Voice Passcode (e.g., 'Authorize: <code\>') to proceed."
            )
        return await func(*args, **kwargs)
    return wrapper


class BaseTool:
    """Base class for all JARVIS tools."""

    name: str = "base_tool"
    description: str = "Base tool description"
    requires_auth: bool = False

    async def execute(self, **kwargs) -> str:
        raise NotImplementedError("Tool execution must be implemented by subclasses.")

    def get_declaration(self) -> Dict[str, Any]:
        """Returns Gemini-compatible function declaration schema."""
        raise NotImplementedError("Tool declaration schema must be defined.")
