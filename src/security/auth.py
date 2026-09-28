import re
import time
import logging
from typing import Optional
from src.config import get_settings

logger = logging.getLogger("jarvis.security")


class SecurityManager:
    """Manages system unlock state, voice security passphrase verification,

    and session elevations for sensitive actions.
    """

    def __init__(self):
        self.settings = get_settings()
        self.is_unlocked: bool = False
        self.unlocked_at: Optional[float] = None
        self.failed_attempts: int = 0
        self.max_failed_attempts: int = 3
        self.lockout_until: Optional[float] = None
        self.lockout_duration_seconds: int = 60

    def _normalize_phrase(self, phrase: str) -> str:
        """Normalizes spoken or typed phrases for robust comparison."""
        cleaned = phrase.lower().strip()
        # Replace common spoken numbers or symbols
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Word replacements for spoken numbers
        replacements = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        }
        words = cleaned.split()
        normalized_words = [replacements.get(w, w) for w in words]
        return " ".join(normalized_words).strip()

    def check_lockout(self) -> tuple[bool, int]:
        """Returns (is_locked_out, remaining_seconds)."""
        if self.lockout_until:
            now = time.time()
            if now < self.lockout_until:
                return True, int(self.lockout_until - now)
            # Lockout expired
            self.lockout_until = None
            self.failed_attempts = 0
        return False, 0

    def is_session_active(self) -> bool:
        """Checks if current session is active and not expired."""
        if not self.is_unlocked:
            return False

        if self.unlocked_at is None:
            self.is_unlocked = False
            return False

        elapsed_minutes = (time.time() - self.unlocked_at) / 60.0
        if elapsed_minutes > self.settings.SESSION_TIMEOUT_MINUTES:
            logger.info("Session expired. Auto-locking JARVIS.")
            self.lock_system()
            return False

        return True

    def verify_passcode(self, candidate: str) -> tuple[bool, str]:
        """Verifies candidate spoken or typed passcode against configured secret.

        Returns (success: bool, message: str)
        """
        is_locked, remaining = self.check_lockout()
        if is_locked:
            return False, f"Security lockout active. Try again in {remaining} seconds."

        expected = self._normalize_phrase(self.settings.JARVIS_SECRET_CODE)
        received = self._normalize_phrase(candidate)

        # Check if expected passphrase exists anywhere in candidate phrase
        # E.g., user says: "Jarvis my authorization code is omega protocol 9"
        if expected in received or received == expected:
            self.is_unlocked = True
            self.unlocked_at = time.time()
            self.failed_attempts = 0
            self.lockout_until = None
            logger.info("Voice authorization successful. System unlocked.")
            return True, "Voice authorization confirmed. Access granted. Welcome back, Boss."

        self.failed_attempts += 1
        logger.warning(f"Passcode verification failed. Attempt {self.failed_attempts}/{self.max_failed_attempts}")

        if self.failed_attempts >= self.max_failed_attempts:
            self.lockout_until = time.time() + self.lockout_duration_seconds
            return False, f"Maximum attempts exceeded. Security lockout engaged for {self.lockout_duration_seconds} seconds."

        remaining_tries = self.max_failed_attempts - self.failed_attempts
        return False, f"Authorization failed. Incorrect passphrase. {remaining_tries} attempts remaining."

    def lock_system(self):
        """Immediately locks JARVIS."""
        self.is_unlocked = False
        self.unlocked_at = None
        logger.info("JARVIS locked.")

    def get_status(self) -> dict:
        """Returns security status dictionary."""
        is_locked, remaining = self.check_lockout()
        return {
            "unlocked": self.is_session_active(),
            "locked_out": is_locked,
            "lockout_remaining_seconds": remaining,
            "session_timeout_minutes": self.settings.SESSION_TIMEOUT_MINUTES
        }


# Global security manager singleton
security_manager = SecurityManager()
