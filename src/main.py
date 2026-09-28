import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from src.config import get_settings
from src.database.session import init_db
from src.security.auth import security_manager
from src.agents.orchestrator import jarvis_orchestrator
from src.voice.tts import tts_engine
from src.tools.system_tool import system_tool

import asyncio
from src.voice.stt import stt_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("jarvis.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for JARVIS service."""
    logger.info("Initializing JARVIS Subsystems...")
    try:
        await init_db()
        logger.info("SQLite Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database init warning: {e}")

    logger.info(f"JARVIS Online and listening at http://{settings.HOST}:{settings.PORT}")
    yield
    logger.info("Shutting down JARVIS protocols.")


app = FastAPI(
    title="Project JARVIS",
    description="Multimodal Autonomous Voice AI Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# Mount UI static assets
ui_dir = os.path.join(os.path.dirname(__file__), "ui")
app.mount("/static", StaticFiles(directory=ui_dir), name="static")


class CommandRequest(BaseModel):
    text: str


class PasscodeUpdateRequest(BaseModel):
    new_code: str


class PasscodeVerifyRequest(BaseModel):
    code: str


class EmailPasswordRequest(BaseModel):
    password: str


@app.get("/")
async def get_index():
    """Serves the Cyber HUD dashboard."""
    index_file = os.path.join(ui_dir, "index.html")
    return FileResponse(index_file)


@app.get("/api/status")
async def get_status():
    """Returns real-time system and security state."""
    sec_status = security_manager.get_status()
    return {
        "status": "online",
        "model": settings.GEMINI_MODEL,
        "security": sec_status,
        "voice": settings.TTS_VOICE,
        "stt_available": stt_engine.is_available()
    }


@app.post("/api/security/set-passcode")
async def set_passcode(req: PasscodeUpdateRequest):
    """Updates the voice security code in memory and persists to .env."""
    success, msg = security_manager.update_passcode(req.new_code)
    return {"success": success, "message": msg, "passcode": req.new_code if success else ""}


@app.post("/api/security/reset-lockout")
async def reset_lockout():
    """Manually resets the lockout cooldown."""
    security_manager.reset_lockout()
    return {"success": True, "message": "Security lockout reset."}


@app.post("/api/config/set-email-password")
async def set_email_password_endpoint(req: EmailPasswordRequest):
    """Updates the Gmail App Password in .env and refreshes mail manager."""
    pwd = req.password.strip().replace(" ", "")
    if len(pwd) < 8:
        return {"success": False, "message": "App password must be at least 8 characters (Google generates a 16-letter code)."}

    from src.security.auth import update_env_var
    saved = update_env_var("EMAIL_APP_PASSWORD", pwd)
    from src.tools.mail_tool import mail_tool
    mail_tool.settings.EMAIL_APP_PASSWORD = pwd
    return {"success": saved, "message": "Gmail App Password saved successfully. Mail automation is active!"}


@app.post("/api/security/unlock")
async def unlock_system(req: PasscodeVerifyRequest):
    """Verifies passcode and returns unlock result."""
    success, msg = security_manager.verify_passcode(req.code)
    audio_b64 = await tts_engine.synthesize_to_base64(msg)
    return {
        "success": success,
        "reply": msg,
        "audio_base64": audio_b64,
        "unlocked": security_manager.is_session_active()
    }


@app.post("/api/voice/listen")
async def listen_and_process():
    """Listens on system microphone via backend STT engine and processes the spoken command."""
    success, text_or_err = await asyncio.to_thread(stt_engine.listen_and_transcribe, 6)
    if not success:
        return {
            "success": False,
            "transcribed": "",
            "reply": f"Voice capture failed: {text_or_err}",
            "audio_base64": "",
            "unlocked": security_manager.is_session_active()
        }

    # Process recognized text
    res = await jarvis_orchestrator.handle_user_input(text_or_err)
    voice_text = res.get("voice_reply", res.get("reply", ""))
    audio_b64 = await tts_engine.synthesize_to_base64(voice_text)

    return {
        "success": True,
        "transcribed": text_or_err,
        "reply": res.get("reply"),
        "audio_base64": audio_b64,
        "unlocked": res.get("unlocked", security_manager.is_session_active())
    }


@app.post("/api/voice/transcribe")
async def transcribe_audio_upload(file: UploadFile = File(...)):
    """Transcribes audio file recorded in browser and processes the command."""
    audio_bytes = await file.read()
    success, text_or_err = await asyncio.to_thread(stt_engine.transcribe_audio_bytes, audio_bytes)
    if not success:
        return {
            "success": False,
            "transcribed": "",
            "reply": f"Voice transcription failed: {text_or_err}",
            "audio_base64": "",
            "unlocked": security_manager.is_session_active()
        }

    res = await jarvis_orchestrator.handle_user_input(text_or_err)
    voice_text = res.get("voice_reply", res.get("reply", ""))
    audio_b64 = await tts_engine.synthesize_to_base64(voice_text)

    return {
        "success": True,
        "transcribed": text_or_err,
        "reply": res.get("reply"),
        "audio_base64": audio_b64,
        "unlocked": res.get("unlocked", security_manager.is_session_active())
    }


@app.post("/api/command")
async def post_command(cmd: CommandRequest):
    """HTTP endpoint to execute a command."""
    result = await jarvis_orchestrator.handle_user_input(cmd.text)
    voice_text = result.get("voice_reply", result.get("reply", ""))
    
    audio_b64 = ""
    if voice_text:
        try:
            audio_b64 = await asyncio.wait_for(tts_engine.synthesize_to_base64(voice_text), timeout=3.0)
        except Exception:
            pass

    return {
        "reply": result.get("reply"),
        "voice_text": voice_text,
        "audio_base64": audio_b64,
        "unlocked": result.get("unlocked", security_manager.is_session_active())
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bi-directional telemetry and audio channel."""
    await websocket.accept()
    logger.info("HUD WebSocket connected.")

    # Send initial status
    await websocket.send_json({
        "type": "status_update",
        "unlocked": security_manager.is_session_active(),
        "model": settings.GEMINI_MODEL
    })

    try:
        while True:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            user_text = data.get("text", "")

            # Process command via Orchestrator
            res = await jarvis_orchestrator.handle_user_input(user_text)
            voice_text = res.get("voice_reply", res.get("reply", ""))

            # Synthesize voice audio with a 2.5s timeout
            audio_b64 = ""
            if voice_text:
                try:
                    audio_b64 = await asyncio.wait_for(tts_engine.synthesize_to_base64(voice_text), timeout=2.5)
                except Exception as tts_err:
                    logger.debug(f"Neural TTS timeout/fallback ({tts_err}); client browser speech will handle voice.")

            # Emit single unified response to HUD
            await websocket.send_json({
                "type": "response",
                "reply": res.get("reply"),
                "voice_text": voice_text,
                "audio_base64": audio_b64,
                "unlocked": res.get("unlocked", security_manager.is_session_active())
            })

    except WebSocketDisconnect:
        logger.info("HUD WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket session error: {e}")


def run():
    """Entry point for launcher."""
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)


if __name__ == "__main__":
    run()
