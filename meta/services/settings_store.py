"""
MAGI Meta Layer — Configurable Settings Store.

All settings are loaded from SQLite on startup and cached in memory.
Write-through: any update is persisted immediately.

Default values are used when a key is not yet in the database.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional

from magi.meta.services import db as _db

# ── Default Values ────────────────────────────────────────────────────────────

DEFAULTS: Dict[str, Any] = {
    # Branding
    "branding.title":           "MAGI Dashboard",
    "branding.subtitle":        "",
    "branding.logo_url":        "",
    "branding.accent_color":    "hsl(217, 91%, 50%)",

    # Theme
    "ui.theme":                 "light",   # "light" | "dark"

    # Server
    "server.host":              "0.0.0.0",
    "server.port":              8765,

    # General
    "general.output_dir":       "magi_outputs",
    "general.default_duration_hours":  8.0,
    "general.default_replications":    30,
    "general.default_seed":            0,

    # LLM (Google only)
    "llm.api_key":              "",
    "llm.model":                "gemini-2.5-flash-preview-04-17",
    "llm.selected_model":       "gemini-2.5-flash-preview-04-17",
    "llm.model_presets": [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemma-4-31b-it",
    ],
    "llm.temperature":          0.3,

    # Agent
    "agent.system_prompt":      (
        "You are MAGI, an AI manufacturing optimization agent. "
        "Monitor the Silverline assembly line, analyse KPIs, and apply lean "
        "improvements via the available tools. Prioritise worker safety and "
        "ergonomics. Always explain your reasoning before calling tools."
    ),
    "agent.cycle_interval_sim_seconds":  300.0,   # how often to run a monitoring cycle (sim time)
    "agent.max_tool_calls_per_cycle":    5,
    "agent.auto_monitoring":             True,
    "agent.fatigue_alert_threshold":     0.65,    # 0–1 normalised fatigue score

    # Default ConfigState overrides applied at sim start
    "sim.default_robot_speed_factor":           1.0,
    "sim.default_takt_time_seconds":            60.0,
    "sim.default_buffer_capacity":              5,
    "sim.default_inter_arrival_jitter_cv":      0.05,
    "sim.default_cw_worker_id":                 "001",
    "sim.default_mw_worker_id":                 "001",
}

# ── In-memory cache ───────────────────────────────────────────────────────────

_cache: Dict[str, Any] = {}
_loaded: bool = False
_lock = asyncio.Lock()
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _validate_model_id(value: Any, key: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    model_id = value.strip()
    if not model_id:
        raise ValueError(f"{key} cannot be empty")
    if not _MODEL_ID_RE.match(model_id):
        raise ValueError(f"{key} has invalid format")
    return model_id


def validate_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(updates)
    if "llm.model" in normalized:
        normalized["llm.model"] = _validate_model_id(normalized["llm.model"], "llm.model")
    if "llm.selected_model" in normalized:
        normalized["llm.selected_model"] = _validate_model_id(normalized["llm.selected_model"], "llm.selected_model")
    if "llm.model_presets" in normalized:
        presets = normalized["llm.model_presets"]
        if not isinstance(presets, list):
            raise ValueError("llm.model_presets must be a list of strings")
        normalized["llm.model_presets"] = [_validate_model_id(item, "llm.model_presets[]") for item in presets]
    return normalized


async def load() -> None:
    """Load all settings from SQLite into the in-memory cache. Call once at startup."""
    global _loaded
    async with _lock:
        stored = await _db.get_all_settings()
        _cache.clear()
        _cache.update(DEFAULTS)
        _cache.update(stored)
        _loaded = True


async def get(key: str, default: Any = None) -> Any:
    """Get a setting value. Falls back to default if not set."""
    if not _loaded:
        await load()
    return _cache.get(key, default)


async def set(key: str, value: Any) -> None:
    """Set a setting value and persist to SQLite."""
    async with _lock:
        _cache[key] = value
    await _db.set_setting(key, value)


async def set_many(updates: Dict[str, Any]) -> None:
    """Set multiple setting values atomically."""
    updates = validate_updates(updates)
    async with _lock:
        _cache.update(updates)
    await _db.set_many_settings(updates)


async def get_all() -> Dict[str, Any]:
    """Return a snapshot of all settings (merged defaults + stored)."""
    if not _loaded:
        await load()
    return dict(_cache)


async def reset_to_defaults() -> None:
    """Reset all settings to defaults (writes defaults to DB)."""
    async with _lock:
        _cache.clear()
        _cache.update(DEFAULTS)
    await _db.set_many_settings(DEFAULTS)
