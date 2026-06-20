"""
LLM Configuration Manager — manage multiple LLM presets at runtime.

Stores custom LLM configurations in `llm_config.json`. Supports:
- Multiple named presets (e.g. "default", "openai", "deepseek", etc.)
- Each preset contains: api_url, api_key, model, temperature, max_tokens, extra_params
- One preset is marked as "active" — used when no explicit preset is specified
- Falls back to environment variables (config.py) for the default preset
"""

import json
import logging
from pathlib import Path
import uuid

import config

logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / "llm_config.json"


def _default_preset():
    """Build the default preset from environment variables."""
    return {
        "id": "default",
        "name": "默认配置 (环境变量)",
        "api_url": config.LLM_API_URL,
        "api_key": config.LLM_API_KEY,
        "model": config.LLM_MODEL,
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": 4096,
        "extra_headers": {},
        "is_default": True,
    }


def _load_config():
    """Load llm_config.json, return a dict with 'active_id' and 'presets' list."""
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载LLM配置失败: {e}")
        return None


def _save_config(data):
    """Persist llm_config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存LLM配置失败: {e}")
        raise


def _ensure_config():
    """Ensure config file exists; initialise with defaults if not."""
    data = _load_config()
    if data is not None:
        return data
    data = {
        "active_id": "default",
        "presets": [_default_preset()],
    }
    _save_config(data)
    return data


# ── Public API ───────────────────────────────────────────────────────────────


def get_all_presets():
    """Return all presets (list of dicts)."""
    data = _ensure_config()
    return data["presets"]


def get_active_preset():
    """Return the currently active preset dict."""
    data = _ensure_config()
    active_id = data.get("active_id", "default")
    for p in data["presets"]:
        if p["id"] == active_id:
            return p
    # Fallback to first preset
    return data["presets"][0] if data["presets"] else _default_preset()


def get_preset_by_id(preset_id):
    """Return a specific preset by id, or None."""
    data = _ensure_config()
    for p in data["presets"]:
        if p["id"] == preset_id:
            return p
    return None


def set_active_preset(preset_id):
    """Set the active preset by id."""
    data = _ensure_config()
    for p in data["presets"]:
        if p["id"] == preset_id:
            data["active_id"] = preset_id
            _save_config(data)
            return True
    return False


def add_preset(preset):
    """Add a new preset. Returns the created preset (with generated id)."""
    data = _ensure_config()
    new_preset = {
        "id": preset.get("id") or f"custom_{uuid.uuid4().hex[:8]}",
        "name": preset.get("name", "自定义配置"),
        "api_url": preset.get("api_url", ""),
        "api_key": preset.get("api_key", ""),
        "model": preset.get("model", ""),
        "temperature": preset.get("temperature", 0.2),
        "max_tokens": preset.get("max_tokens", 4096),
        "extra_headers": preset.get("extra_headers", {}),
        "is_default": False,
    }
    data["presets"].append(new_preset)
    _save_config(data)
    return new_preset


def update_preset(preset_id, updates):
    """Update an existing preset by id. Returns the updated preset or None."""
    data = _ensure_config()
    for p in data["presets"]:
        if p["id"] == preset_id:
            # Don't allow changing id or is_default on the env-var preset
            if p.get("is_default"):
                allowed_keys = {"name", "api_url", "api_key", "model", "temperature", "max_tokens", "extra_headers"}
            else:
                allowed_keys = {"name", "api_url", "api_key", "model", "temperature", "max_tokens", "extra_headers"}
            for key in allowed_keys:
                if key in updates:
                    p[key] = updates[key]
            _save_config(data)
            return p
    return None


def delete_preset(preset_id):
    """Delete a preset by id. Cannot delete the 'default' preset."""
    data = _ensure_config()
    if preset_id == "default":
        return False
    original_len = len(data["presets"])
    data["presets"] = [p for p in data["presets"] if p["id"] != preset_id]
    if len(data["presets"]) < original_len:
        # If we deleted the active preset, switch to default
        if data["active_id"] == preset_id:
            data["active_id"] = "default"
        _save_config(data)
        return True
    return False


def get_llm_params(preset_id=None):
    """
    Return a ready-to-use dict for making LLM API calls.
    If preset_id is given, use that preset; otherwise use the active one.
    Keys: api_url, api_key, model, temperature, max_tokens, extra_headers
    """
    if preset_id:
        preset = get_preset_by_id(preset_id)
        if not preset:
            preset = get_active_preset()
    else:
        preset = get_active_preset()
    return {
        "api_url": preset["api_url"],
        "api_key": preset["api_key"],
        "model": preset["model"],
        "temperature": preset["temperature"],
        "max_tokens": preset.get("max_tokens", 4096),
        "extra_headers": preset.get("extra_headers", {}),
    }


def reset_to_defaults():
    """Reset configuration to environment-variable defaults."""
    data = {
        "active_id": "default",
        "presets": [_default_preset()],
    }
    _save_config(data)
    return data
