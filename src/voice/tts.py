import os
import io
import asyncio
import logging
import base64
from typing import Optional
from src.config import get_settings

logger = logging.getLogger("jarvis.voice.tts")


class TextToSpeechEngine:
    """High-fidelity Neural Text-to-Speech Engine powered by edge-tts (100% Free)."""

    def __init__(self):
        self.settings = get_settings()
        self.voice = self.settings.TTS_VOICE
        self.rate = self.settings.TTS_RATE
        self.pitch = self.settings.TTS_PITCH

    async def synthesize_to_bytes(self, text: str) -> bytes:
        """Synthesizes text into MP3 audio bytes asynchronously."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
            audio_stream.seek(0)
            return audio_stream.read()
        except ImportError:
            logger.warning("edge-tts not installed. Voice synthesis fallback to empty audio.")
            return b""
        except Exception as e:
            logger.error(f"TTS Synthesis error: {e}")
            return b""

    async def synthesize_to_base64(self, text: str) -> str:
        """Returns synthesized audio encoded in base64 for direct browser playback."""
        audio_bytes = await self.synthesize_to_bytes(text)
        if not audio_bytes:
            return ""
        return base64.b64encode(audio_bytes).decode("utf-8")

    async def save_to_file(self, text: str, output_path: str) -> bool:
        """Synthesizes text and writes directly to an audio file."""
        try:
            audio_bytes = await self.synthesize_to_bytes(text)
            if not audio_bytes:
                return False
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return True
        except Exception as e:
            logger.error(f"Failed to write audio to file: {e}")
            return False


# Global singleton TTS engine
tts_engine = TextToSpeechEngine()
