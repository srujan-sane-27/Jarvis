import io
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

    def is_available(self) -> bool:
        """Checks if speech recognition backend is initialized."""
        if not self.recognizer:
            self._init_recognizer()
        return self.recognizer is not None

    def listen_and_transcribe(self, timeout: int = 5) -> tuple[bool, str]:
        """Listens on the local microphone and transcribes.

        Returns (success: bool, text_or_error: str)
        """
        if not self.is_available():
            return False, "Speech recognition library is not available on server."

        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                logger.info("Listening on system microphone for voice input...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                text = self.recognizer.recognize_google(audio)
                logger.info(f"Transcribed audio: '{text}'")
                return True, text
        except sr.WaitTimeoutError:
            logger.info("Speech recognition timed out: no voice detected.")
            return False, "Listening timed out. No speech was detected."
        except sr.UnknownValueError:
            logger.info("Speech recognition could not understand audio.")
            return False, "Could not understand audio. Please speak clearly into the microphone."
        except sr.RequestError as e:
            logger.warning(f"Google Speech API error: {e}")
            return False, f"Speech recognition service error: {str(e)}"
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return False, f"Microphone error: {str(e)}"

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> tuple[bool, str]:
        """Transcribes incoming audio file bytes (e.g. from browser recording)."""
        if not self.is_available():
            return False, "Speech recognition engine not initialized."

        try:
            import speech_recognition as sr
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                return True, text
        except Exception as e:
            logger.warning(f"Audio bytes transcription failed: {e}")
            return False, str(e)


# Global singleton STT engine
stt_engine = SpeechToTextEngine()
