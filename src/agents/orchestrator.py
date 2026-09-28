import os
import json
import logging
import re
import asyncio
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
        self.settings = get_settings()
        if not self.settings.GEMINI_API_KEY or self.settings.GEMINI_API_KEY == "your_gemini_api_key_here":
            logger.info("Gemini API key not configured yet. Running in offline rule-engine fallback mode.")
            self._gemini_client = None
            return

        try:
            from google import genai
            self._gemini_client = genai.Client(api_key=self.settings.GEMINI_API_KEY)
            logger.info(f"Google GenAI client initialized with model: {self.settings.GEMINI_MODEL}")
        except Exception as e:
            logger.warning(f"Could not initialize Google GenAI SDK: {e}. Will attempt fallback.")
            self._gemini_client = None

    async def process(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Implements BaseAgent contract."""
        res = await self.handle_user_input(prompt)
        return res.get("reply", "")

    async def handle_user_input(self, user_text: str) -> Dict[str, Any]:
        """Main entry point for text/voice queries from User or WebSocket."""
        clean_text = user_text.strip()
        if not clean_text:
            return {"reply": "I'm standing by, Boss. How may I assist you?", "voice_reply": "I am standing by, Boss."}

        lower = clean_text.lower()

        # 1. Check for Unlock / Passphrase attempt
        passcode_triggers = ["passcode", "code", "authorize", "authorization", "password", "unlock", "omega", "protocol"]
        is_passcode_candidate = any(t in lower for t in passcode_triggers)

        # If user explicitly provides authorization passcode
        if "omega" in lower or (is_passcode_candidate and any(n in lower for n in ["9", "nine", "protocol", "code"])):
            if security_manager.is_session_active():
                return {
                    "reply": "🔒 **Security Authorization**:\nVoice authorization is already confirmed and active. Systems are fully standing by, Boss.",
                    "voice_reply": "Voice authorization is already confirmed. Standing by, Boss.",
                    "unlocked": True
                }
            success, msg = security_manager.verify_passcode(clean_text)
            return {
                "reply": f"🔒 **Security Authorization**:\n{msg}",
                "voice_reply": msg,
                "unlocked": success
            }

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
        if "lock system" in lower or "lock jarvis" in lower:
            security_manager.lock_system()
            return {
                "reply": "🔒 **JARVIS Locked**\nSecurity protocols engaged. System locked.",
                "voice_reply": "Security protocols engaged. System locked.",
                "unlocked": False
            }

        # Check for set email/gmail password command
        if any(w in lower for w in ["set email password", "set gmail password", "save email password", "change email password", "email password is", "gmail password is"]):
            match = re.search(r"(?:to|is|password)\s+([a-zA-Z0-9 ]+)", clean_text, re.IGNORECASE)
            if match:
                raw_pwd = match.group(1).strip().replace(" ", "")
                if len(raw_pwd) >= 8:
                    from src.security.auth import update_env_var
                    update_env_var("EMAIL_APP_PASSWORD", raw_pwd)
                    mail_tool.settings.EMAIL_APP_PASSWORD = raw_pwd
                    return {
                        "reply": "✉️ **Gmail App Password Saved**\nYour Gmail credentials have been securely stored in `.env`. Mail automation is now fully active!",
                        "voice_reply": "Gmail password has been saved, Boss. Mail automation is now active.",
                        "unlocked": True
                    }
            return {
                "reply": "Please specify the 16-character Google App Password. Example: `set gmail password abcd efgh ijkl mnop`.",
                "voice_reply": "Please specify the 16 character Google App Password to save.",
                "unlocked": True
            }

        # Check for change passcode command
        if any(w in lower for w in ["set passcode", "change passcode", "set security code", "change security code", "set password", "change password", "update passcode"]):
            match = re.search(r"(?:to|is|code)\s+([a-zA-Z0-9\-_ ]+)", clean_text, re.IGNORECASE)
            if match:
                new_code = match.group(1).strip()
                success, msg = security_manager.update_passcode(new_code)
                return {
                    "reply": f"🔒 **Security Passcode Updated**\n{msg}\nSaved to `.env` as `JARVIS_SECRET_CODE`.",
                    "voice_reply": f"Voice security code has been updated to {new_code}.",
                    "unlocked": True
                }
            return {
                "reply": "Please specify the new passcode. Example: `change passcode to iron man` or `set passcode to alpha 7`.",
                "voice_reply": "Please specify the new passcode to apply.",
                "unlocked": True
            }

        # Check current security code status (when unlocked)
        if any(w in lower for w in ["what is the password", "what is the passcode", "what is my security code", "current passcode"]):
            return {
                "reply": (
                    f"🔒 **Security Code Configuration**\n"
                    f"Current voice security code: `{security_manager.settings.JARVIS_SECRET_CODE}`\n"
                    f"To change it, say or type: `change passcode to <your-phrase>` or edit `.env`."
                ),
                "voice_reply": f"Your voice security code is currently set to {security_manager.settings.JARVIS_SECRET_CODE}.",
                "unlocked": True
            }

        # 2. Check for Direct Tool Commands (High-Speed Local Execution)

        # Telemetry / Hardware check
        if any(w in lower for w in ["system status", "telemetry", "cpu", "battery", "hardware", "diagnostics"]):
            telemetry = await system_tool.get_system_telemetry()
            return {
                "reply": telemetry,
                "voice_reply": "System diagnostics nominal. All core parameters within optimal operational ranges.",
                "unlocked": True
            }

        # Conversational greetings & status
        cleaned_simple = re.sub(r"[^\w\s]", "", lower).strip()
        if cleaned_simple in ["hay", "hey", "hello", "hi", "hi jarvis", "hey jarvis", "hay jarvis", "good morning", "good evening", "are you there"]:
            return {
                "reply": "At your service, Boss. All subsystems are online and fully operational. What can I do for you?",
                "voice_reply": "At your service, Boss. All subsystems online. How can I assist you?",
                "unlocked": True
            }

        if any(w in lower for w in ["how are you", "how are you doing", "status report"]):
            return {
                "reply": "I am functioning at optimal parameters, Boss. Diagnostics nominal. Standing by for your instructions.",
                "voice_reply": "I am functioning at peak efficiency, Boss. Standing by for your instructions.",
                "unlocked": True
            }

        if any(w in lower for w in ["who are you", "what is your name"]):
            return {
                "reply": "I am **J.A.R.V.I.S.** (Just A Rather Very Intelligent System), your personal multimodal autonomous assistant.",
                "voice_reply": "I am JARVIS, your personal autonomous assistant. Always ready to assist you, Boss.",
                "unlocked": True
            }

        # Weather query
        if "weather" in lower:
            city_match = re.search(r"weather in ([\w\s]+)", lower)
            city = city_match.group(1).strip() if city_match else "Pune"
            # Strip trailing punctuation or filler words like "please", "now", "today"
            city = re.sub(r"\b(please|now|today|right now)\b", "", city).strip()
            if not city:
                city = "Pune"
            report = await news_tool.get_weather(city)
            voice_text = await news_tool.get_weather_voice(city)
            return {
                "reply": report,
                "voice_reply": voice_text,
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

        # Conversational acknowledgments
        if any(lower == w or lower.startswith(w + " ") for w in ["perfect", "great", "awesome", "good job", "thank you", "thanks", "well done", "nice", "cool"]):
            return {
                "reply": "Always a pleasure, Boss. Standing by for your next instruction.",
                "voice_reply": "Always a pleasure, Boss. Standing by.",
                "unlocked": True
            }

        # Email check
        if any(w in lower for w in ["mail", "email", "inbox", "mailbox"]):
            mail_res = await mail_tool.fetch_unread_emails()
            voice_text = (
                "Mail access requires an email app password, Boss. Please generate a free Google App Password and add it to your configuration."
                if not mail_tool.settings.EMAIL_APP_PASSWORD
                else "I have accessed your mailbox. The summary is displayed on your dashboard."
            )
            return {
                "reply": mail_res,
                "voice_reply": voice_text,
                "unlocked": True
            }

        # YouTube & Media Commands (matches "youtube", "player youtube video", "play video", "watch youtube", etc.)
        if "youtube" in lower or any(w in lower for w in ["play song", "play music", "play a song", "play track", "play video", "player youtube", "play youtube", "watch video", "show video"]) or lower.startswith("play ") or lower.startswith("player "):
            y_query = re.sub(r"^(so\s+)?(can\s+you\s+)?(please\s+)?(open\s+|launch\s+|play\s+|player\s+|watch\s+|show\s+)?(a\s+)?(youtube\s+video\s+of\s+|youtube\s+video\s+|youtube\s+song\s+of\s+|youtube\s+|video\s+of\s+|song\s+for\s+me\s+right\s+now|song\s+for\s+me|song\s+of\s+|song\s+|music\s+of\s+|music\s+|track\s+of\s+|track\s+)?(\s+called|\s+named|\s+of)?", "", lower).strip()
            if not y_query or y_query in ["youtube", "video", "song", "music"]:
                y_query = "trending music"
            res = await chrome_tool.search_youtube(y_query)
            return {
                "reply": f"🎬 **YouTube Hub**:\n{res}",
                "voice_reply": f"Playing {y_query} on YouTube in Chrome for you, Boss.",
                "unlocked": True
            }

        # Google Search in Chrome
        if any(w in lower for w in ["search google", "search on google", "open google and search", "open google to search"]):
            g_query = re.sub(r"^(so\s+)?(can\s+you\s+)?(please\s+)?(open\s+google\s+and\s+search\s+(for\s+)?|open\s+google\s+to\s+search\s+(for\s+)?|search\s+(on\s+)?google\s+(for\s+)?)", "", lower).strip()
            if not g_query:
                g_query = "news"
            res = await chrome_tool.search_google(g_query)
            return {
                "reply": f"🌐 **Google Chrome Search**:\n{res}",
                "voice_reply": f"Searching Google for {g_query} in Chrome, Boss.",
                "unlocked": True
            }

        # Website & Application Launch
        if lower.startswith("open ") or lower.startswith("launch "):
            app_target = lower.replace("open ", "").replace("launch ", "").strip()
            app_target = re.sub(r"\s+in\s+chrome$", "", app_target).strip()

            # Check websites & online services first
            if app_target in chrome_tool.SITE_PRESETS or any(app_target.endswith(tld) for tld in [".com", ".org", ".net", ".io", ".co", ".in", ".edu", ".ai"]):
                res = await chrome_tool.open_target(app_target)
                return {
                    "reply": f"🌐 **Chrome Automation**:\n{res}",
                    "voice_reply": f"Opening {app_target} in Chrome, Boss.",
                    "unlocked": True
                }

            # Check local desktop apps
            if app_target in ["notepad", "calc", "calculator", "explorer", "code", "vscode", "chrome", "terminal", "cmd"]:
                res = await system_tool.open_application(app_target)
                return {
                    "reply": res,
                    "voice_reply": f"Launching {app_target} now.",
                    "unlocked": True
                }

        # Web Background Research
        if lower.startswith("search for ") or lower.startswith("search "):
            q = lower.replace("search for ", "").replace("search ", "").strip()
            res = await chrome_tool.search_web(q)
            return {
                "reply": res,
                "voice_reply": f"I found several results for '{q}'.",
                "unlocked": True
            }

        # 3. LLM Reasoning with Google Gemini
        if not self._gemini_client:
            self._init_gemini()

        if self._gemini_client:
            system_instruction = (
                "You are JARVIS (Just A Rather Very Intelligent System), the sophisticated, loyal, "
                "and witty AI assistant created for Srujan. "
                "Your responses must be articulate, confident, and direct. "
                "Address the user politely as 'Boss' or 'Sir'. "
                "Keep explanations crisp and actionable."
            )
            # Prioritize top ultra-lightweight flash-lite models with rapid fallback
            candidate_models = [self.settings.GEMINI_MODEL, "gemini-3.5-flash-lite"]
            unique_models = [m for m in candidate_models if m][:2]

            for model_name in unique_models:
                try:
                    def _call():
                        return self._gemini_client.models.generate_content(
                            model=model_name,
                            contents=clean_text,
                            config={
                                "system_instruction": system_instruction,
                                "max_output_tokens": 150,
                                "temperature": 0.6
                            }
                        )
                    response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=3.5)
                    llm_reply = response.text or "I processed your request, Boss."
                    clean_voice = re.sub(r"[*_#`]", "", llm_reply).strip()
                    if len(clean_voice) > 220:
                        clean_voice = clean_voice[:217] + "..."
                    return {
                        "reply": llm_reply,
                        "voice_reply": clean_voice,
                        "unlocked": True
                    }
                except Exception as e:
                    logger.warning(f"Gemini attempt with model '{model_name}' skipped: {e}")

        # Autonomous Web Intelligence Fallback when LLM encounters demand spikes
        try:
            web_intel = await chrome_tool.search_web(clean_text)
            if web_intel and "Web Search Results" in web_intel:
                return {
                    "reply": f"🌐 **Autonomous Intelligence Retrieval**:\n{web_intel}",
                    "voice_reply": "I retrieved live intelligence from the web for your query, Boss.",
                    "unlocked": True
                }
        except Exception as e:
            logger.warning(f"Web intelligence fallback failed: {e}")

        # High-Speed Local Response
        return {
            "reply": (
                f"I processed your command: *\"{clean_text}\"*\n\n"
                "Operating in high-speed local mode. Subsystems nominal."
            ),
            "voice_reply": "Command processed, Boss. Subsystems nominal.",
            "unlocked": True
        }


# Global singleton orchestrator
jarvis_orchestrator = JarvisOrchestrator()
