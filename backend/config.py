import os
import json
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_LLM_MODEL: str = "qwen2:0.5b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_DB_DIR: str = os.path.join(os.path.dirname(__file__), "chroma_db")
    REGISTRY_PATH: str = os.path.join(os.path.dirname(__file__), "models", "model_registry.json")
    
    # RAG Chunking & Context Window Parameters
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100
    MAX_CONTEXT_CHARS: int = 16000
    
    # CORS Security Origins
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    @property
    def model_registry(self) -> dict:
        if os.path.exists(self.REGISTRY_PATH):
            with open(self.REGISTRY_PATH, 'r') as f:
                return json.load(f)
        return {}

settings = Settings()

