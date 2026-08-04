import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from app.schemas.resume import ResumeSchema


def test_nvidia_connection():
    print(f"Testing NVIDIA API Key: {settings.NVIDIA_API_KEY[:10]}...")
    print(f"Testing Model: {settings.NVIDIA_MODEL_NAME}")

    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.1
    )

    print("Sending test request to NVIDIA NIM...")
    try:
        response = llm.invoke("Hello! Say 'NVIDIA AI API is working!'")
        print(f"Direct Response: {response.content}")
    except Exception as e:
        print(f"Direct LLM Call Error: {e}")

    print("\nTesting Structured Output with Pydantic...")
    try:
        structured_llm = llm.with_structured_output(ResumeSchema)
        res = structured_llm.invoke("Full name: John Doe, Email: john@example.com, Skills: Python, React")
        print(f"Structured Output Result: {res}")
    except Exception as e:
        print(f"Structured Output Error: {e}")


if __name__ == "__main__":
    test_nvidia_connection()
