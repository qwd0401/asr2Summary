"""
Centralized configuration loaded from environment variables.

Add `python-dotenv` to requirements.txt and call `load_dotenv()` at app startup
to load `.env` automatically. Falls back to defaults if env vars are missing
so the app still runs in development.
"""

import os
from pathlib import Path
import secrets


def _load_dotenv():
    """Lightweight .env loader (no python-dotenv dependency required)."""
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            # Don't overwrite already-set env vars
            os.environ.setdefault(key, value)
    except Exception:
        pass


_load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ===== Server =====
PORT = _get_int("PORT", 5000)
HOST = _get("HOST", "0.0.0.0")
FLASK_ENV = _get("FLASK_ENV", "production")

# ===== Security =====
# Auto-generate SECRET_KEY in development, require in production
_env_secret = _get("SECRET_KEY", "")
if _env_secret:
    SECRET_KEY = _env_secret
elif FLASK_ENV == "production":
    SECRET_KEY = ""  # Will be caught by validate_production()
else:
    SECRET_KEY = secrets.token_hex(32)  # Auto-generate for dev

# ===== ASR (speech-to-text) =====
ASR_API_KEY = _get("ASR_API_KEY", "")
ASR_API_URL = _get("ASR_API_URL", "https://api.siliconflow.cn/v1/audio/transcriptions")
ASR_MODEL = _get("ASR_MODEL", "FunAudioLLM/SenseVoiceSmall")

# ===== LLM (meeting summary) =====
LLM_API_KEY = _get("LLM_API_KEY", "")
LLM_API_URL = _get("LLM_API_URL", "https://api.linkapi.org/v1/chat/completions")
LLM_MODEL = _get("LLM_MODEL", "gemini-2.5-flash-preview-05-20")
LLM_TEMPERATURE = _get_float("LLM_TEMPERATURE", 0.2)

# ===== Limits =====
MAX_UPLOAD_MB = _get_int("MAX_UPLOAD_MB", 100)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
API_TIMEOUT_SEC = _get_int("API_TIMEOUT_SEC", 300)


class ConfigError(RuntimeError):
    """Raised when a required config value is missing in production."""


def validate_production():
    """Call before starting in production to fail-fast on missing secrets."""
    if FLASK_ENV != "production":
        return
    missing = []
    if not ASR_API_KEY or ASR_API_KEY == "your-siliconflow-api-key":
        missing.append("ASR_API_KEY")
    if not LLM_API_KEY or LLM_API_KEY == "your-llm-api-key":
        missing.append("LLM_API_KEY")
    if not SECRET_KEY:
        missing.append("SECRET_KEY")
    if missing:
        raise ConfigError(
            f"Missing required env vars for production: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in real values."
        )
