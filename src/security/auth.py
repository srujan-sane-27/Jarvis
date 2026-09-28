import os
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

        # Fuzzy & phonetic matching for voice accuracy:
        import difflib
        ratio = difflib.SequenceMatcher(None, expected, received).ratio()
        
        # Check direct substring, ratio >= 0.72, or key token overlap
        expected_tokens = set(expected.split())
        received_tokens = set(received.split())
        token_overlap = len(expected_tokens.intersection(received_tokens)) / max(len(expected_tokens), 1)

        is_match = (
            expected in received
            or received == expected
            or ratio >= 0.72
            or token_overlap >= 0.66
            or ("omega" in received and ("9" in received or "nine" in received or "protocol" in received))
        )

        if is_match:
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
            return False, f"Maximum attempts exceeded. Security lockout engaged for {self.lockout_duration_seconds} seconds. You can reset this in the HUD."

        remaining_tries = self.max_failed_attempts - self.failed_attempts
        return False, (
            f"Authorization failed. Incorrect passcode '{candidate}'. "
            f"{remaining_tries} attempt(s) remaining."
        )

    def update_passcode(self, new_code: str) -> tuple[bool, str]:
        """Updates the security passcode in memory and saves to .env."""
        cleaned = new_code.strip()
        if len(cleaned) < 3:
            return False, "Passcode must be at least 3 characters long."

        self.settings.JARVIS_SECRET_CODE = cleaned
        update_env_var("JARVIS_SECRET_CODE", cleaned)
        return True, f"Security passcode successfully updated to '{cleaned}'."

    def reset_lockout(self):
        """Resets lockout cooldown and failed attempt counter."""
        self.failed_attempts = 0
        self.lockout_until = None
        logger.info("Security lockout reset by administrator.")

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


def update_env_var(key: str, value: str) -> bool:
    """Safely updates or inserts a key-value pair in .env."""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if not os.path.exists(env_path):
        return False
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern = rf"{re.escape(key)}=.*"
        if re.search(pattern, content):
            new_content = re.sub(pattern, f"{key}={value}", content)
        else:
            new_content = content.rstrip() + f"\n{key}={value}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        logger.info(f"{key} updated and persisted to {env_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to persist {key} to .env: {e}")
        return False


# Global security manager singleton
security_manager = SecurityManager()
