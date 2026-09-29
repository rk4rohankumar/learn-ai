from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
LLM_PROVIDER="anthropic"
LLM_PROVIDER_MODEL="claude-haiku-4-5"

SYSTEM_PROMPT = (
    "You are a helpful, concise assistant. "
    "Use the available tools when a question needs live data; "
    "otherwise answer directly."
)