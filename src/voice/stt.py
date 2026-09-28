import logging
from typing import Optional

logger = logging.getLogger("jarvis.voice.stt")


class SpeechToTextEngine:
    """Handles local microphone capture and audio transcription."""

    def __init__(self):
        self.recognizer = None
        self._init_recognizer()

    def _init_recognizer(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            logger.info("Speech recognition engine initialized.")
        except ImportError:
            logger.warning("speech_recognition library not available. Client-side Web Speech will be primary.")

    def listen_and_transcribe(self, timeout: int = 5) -> Optional[str]:
        """Listens on the local microphone and transcribes using free Google Speech API."""
        if not self.recognizer:
            return None

        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                logger.info("Listening for voice input...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio)
                logger.info(f"Transcribed audio: '{text}'")
                return text
        except Exception as e:
            logger.debug(f"Speech recognition passive or timeout: {e}")
            return None


# Global singleton STT engine
stt_engine = SpeechToTextEngine()
