import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
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
        "voice": settings.TTS_VOICE
    }


@app.post("/api/command")
async def post_command(cmd: CommandRequest):
    """HTTP endpoint to execute a command."""
    result = await jarvis_orchestrator.handle_user_input(cmd.text)
    
    # Generate voice audio
    voice_text = result.get("voice_reply", result.get("reply", ""))
    audio_b64 = await tts_engine.synthesize_to_base64(voice_text)

    return {
        "reply": result.get("reply"),
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

            # Generate neural voice audio stream
            voice_text = res.get("voice_reply", res.get("reply", ""))
            audio_b64 = await tts_engine.synthesize_to_base64(voice_text)

            # Emit back to client HUD
            await websocket.send_json({
                "type": "response",
                "reply": res.get("reply"),
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
