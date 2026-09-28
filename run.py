"""Convenience launcher for Project JARVIS."""
import uvicorn
from src.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print(f"\n=======================================================")
    print(f"  [+] Starting JARVIS AI Assistant")
    print(f"  [+] Cyber HUD: http://{settings.HOST}:{settings.PORT}")
    print(f"  [+] Voice Engine: {settings.TTS_VOICE}")
    print(f"  [+] Security Gate: ACTIVE (Say or enter passcode to unlock)")
    print(f"=======================================================\n")
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
