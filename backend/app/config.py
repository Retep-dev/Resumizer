import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_MODEL_NAME: str = os.getenv("NVIDIA_MODEL_NAME", "meta/llama-3.3-70b-instruct")
    CHROMA_DB_DIR: str = os.getenv("CHROMA_DB_DIR", "./chroma_db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

settings = Settings()
