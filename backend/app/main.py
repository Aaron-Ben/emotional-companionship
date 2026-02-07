"""FastAPI application for emotional companionship AI system."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.api.v1 import character, chat, diary
from app.services.character_service import CharacterService
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    init_db()
    print("Database initialized successfully")

    # 检查 Genie-TTS 资源目录
    import os
    from pathlib import Path
    from app.characters.tts import GENIE_DATA_DIR, load_predefined_character

    genie_data_path = Path(GENIE_DATA_DIR) if GENIE_DATA_DIR else None
    if genie_data_path and genie_data_path.exists():
        print(f"Genie-TTS data directory found at {genie_data_path}")
    else:
        print("Genie-TTS data directory not found, will download on first use")

    # 预加载默认角色
    try:
        load_predefined_character("feibi")  # 菲比 - 中文角色
        print("Genie-TTS character 'feibi' loaded successfully")
    except Exception as e:
        print(f"Failed to load Genie-TTS character: {e}")

    yield
    # 关闭时的清理工作（如果需要）
    from app.characters.tts import cleanup
    cleanup()
    print("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="Emotional Companionship AI",
    description="An AI-powered emotional companionship system with customizable characters",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize character service
character_service = CharacterService()

# Store services in app state for dependency injection
app.state.character_service = character_service


# Include routers
app.include_router(character.router)
app.include_router(chat.router)
app.include_router(diary.router)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Emotional Companionship AI API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "characters": "/api/v1/character/",
            "chat": "/api/v1/chat/",
            "diary": "/api/v1/diary/",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "characters_loaded": len(character_service.list_characters())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
