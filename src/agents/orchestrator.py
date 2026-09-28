import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from src.config import get_settings
from src.agents.base import BaseAgent
from src.security.auth import security_manager
from src.tools.mail_tool import mail_tool
from src.tools.chrome_tool import chrome_tool
from src.tools.news_tool import news_tool
from src.tools.system_tool import system_tool
from src.database.memory import memory_store

logger = logging.getLogger("jarvis.orchestrator")


class JarvisOrchestrator(BaseAgent):
    """Central AI Brain coordinating security, tools, memory, and Gemini LLM reasoning."""

    name = "JARVIS_Core"
    description = "Multimodal Autonomous AI Assistant Orchestrator"

    def __init__(self):
        self.settings = get_settings()
        self.conversation_history: List[Dict[str, str]] = []
        self._gemini_client = None
        self._init_gemini()

    def _init_gemini(self):
        """Initializes Google GenAI / GenerativeAI SDK if key is configured."""
        if not self.settings.GEMINI_API_KEY or self.settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            logger.info("Gemini API key not configured yet. Running in offline rule-engine fallback mode.")
            return

        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            logger.info(f"Google GenAI client initialized with model: {self.settings.GEMINI_MODEL}")
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI SDK: {e}. Will attempt fallback.")

    async def process(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Implements BaseAgent contract."""
        res = await self.handle_user_input(prompt)
        return res.get("reply", "")

    async def handle_user_input(self, user_text: str) -> Dict[str, Any]:
        """Main entry point for text/voice queries from User or WebSocket."""
        clean_text = user_text.strip()
        if not clean_text:
            return {"reply": "I'm standing by, Boss. How may I assist you?", "voice_reply": "I am standing by, Boss."}

        # 1. Check for Unlock / Passphrase attempt
        # If user explicitly provides authorization or if system is currently locked
        passcode_triggers = ["passcode", "code", "authorize", "authorization", "password", "unlock", "omega"]
        is_passcode_candidate = any(t in clean_text.lower() for t in passcode_triggers)

        if not security_manager.is_session_active():
            # System is locked!
            if is_passcode_candidate or len(clean_text.split()) <= 4:
                # Attempt passcode verification
                success, msg = security_manager.verify_passcode(clean_text)
                return {
                    "reply": f"🔒 **Security Authorization**:\n{msg}",
                    "voice_reply": msg,
                    "unlocked": success
                }
            else:
                return {
                    "reply": "🔒 **System Locked**\nJARVIS is currently secured. Please speak or enter your Voice Passcode to unlock.",
                    "voice_reply": "System is locked. Please state your authorization code to proceed.",
                    "unlocked": False
                }

        # If system is already unlocked and user explicitly wants to lock it
        if "lock system" in clean_text.lower() or "lock jarvis" in clean_text.lower():
            security_manager.lock_system()
            return {
                "reply": "🔒 **JARVIS Locked**\nSecurity protocols engaged. System locked.",
                "voice_reply": "Security protocols engaged. System locked.",
                "unlocked": False
            }

        # 2. Check for Direct Tool Commands (High-Speed Local Execution)
        lower = clean_text.lower()

        # Telemetry / Hardware check
        if any(w in lower for w in ["system status", "telemetry", "cpu", "battery", "hardware", "diagnostics"]):
            telemetry = await system_tool.get_system_telemetry()
            return {
                "reply": telemetry,
                "voice_reply": "System diagnostics nominal. All core parameters within optimal operational ranges.",
                "unlocked": True
            }

        # Weather query
        if "weather" in lower:
            city_match = re.search(r"weather in ([\w\s]+)", lower)
            city = city_match.group(1).strip() if city_match else "Mumbai"
            report = await news_tool.get_weather(city)
            return {
                "reply": report,
                "voice_reply": f"Here is the current weather update for {city}.",
                "unlocked": True
            }

        # News briefing
        if any(w in lower for w in ["news", "headlines", "briefing"]):
            cat = "tech" if "tech" in lower else "general"
            briefing = await news_tool.get_top_news(cat)
            return {
                "reply": briefing,
                "voice_reply": f"Here is the latest {cat} briefing, Boss.",
                "unlocked": True
            }

        # Email check
        if any(w in lower for w in ["check mail", "read mail", "unread email", "check inbox", "emails"]):
            mail_res = await mail_tool.fetch_unread_emails()
            return {
                "reply": mail_res,
                "voice_reply": "I have accessed the mailbox. Summary displayed on your dashboard.",
                "unlocked": True
            }

        # Desktop app launch
        if lower.startswith("open ") or lower.startswith("launch "):
            app_target = lower.replace("open ", "").replace("launch ", "").strip()
            if app_target in ["notepad", "calc", "calculator", "explorer", "code", "vscode", "chrome"]:
                res = await system_tool.open_application(app_target)
                return {
                    "reply": res,
                    "voice_reply": f"Launching {app_target} now.",
                    "unlocked": True
                }

        # Web Search
        if lower.startswith("search for ") or lower.startswith("search "):
            q = lower.replace("search for ", "").replace("search ", "").strip()
            res = await chrome_tool.search_web(q)
            return {
                "reply": res,
                "voice_reply": f"I found several results for '{q}'.",
                "unlocked": True
            }

        # 3. LLM Reasoning with Google Gemini
        if self._gemini_client:
            try:
                system_instruction = (
                    "You are JARVIS (Just A Rather Very Intelligent System), the sophisticated, loyal, "
                    "and witty AI assistant created for Srujan. "
                    "Your responses must be articulate, confident, and direct. "
                    "Address the user politely as 'Boss' or 'Sir'. "
                    "Keep explanations crisp and actionable."
                )
                response = self._gemini_client.models.generate_content(
                    model=self.settings.GEMINI_MODEL,
                    contents=clean_text,
                    config={"system_instruction": system_instruction}
                )
                llm_reply = response.text or "I processed your request, Boss."
                return {
                    "reply": llm_reply,
                    "voice_reply": llm_reply[:200].replace("*", ""),  # clean for TTS
                    "unlocked": True
                }
            except Exception as e:
                logger.error(f"Gemini API execution error: {e}")

        # Fallback when LLM API key is not yet set
        return {
            "reply": (
                f"I received your command: *\"{clean_text}\"*\n\n"
                "💡 **Notice**: Gemini API Key is not yet configured in `.env`. "
                "You can still use live tools: 'system status', 'weather in <city>', 'tech news', "
                "'check mail', 'open notepad', or 'search <query>'."
            ),
            "voice_reply": "I received your command, Boss. The system is operating in high-speed local mode.",
            "unlocked": True
        }


# Global singleton orchestrator
jarvis_orchestrator = JarvisOrchestrator()
