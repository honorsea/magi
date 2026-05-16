"""
MAGI Meta Layer — SQLite persistence layer.

Tables:
  settings          — key/value store for all configurable settings
  simulations       — simulation session records
  kpi_snapshots     — periodic KPI readings during simulations
  agent_traces      — agent reasoning trace entries
  shortcuts         — user-defined prompt templates and analysis presets
  lean_kg_overrides — user modifications to the Lean Knowledge Graph
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

# Database file location
_DATA_DIR = Path(__file__).parent.parent.parent.parent / "magi_data"
DB_PATH = _DATA_DIR / "magi.db"


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS simulations (
    id              TEXT PRIMARY KEY,
    label           TEXT NOT NULL DEFAULT '',
    mode            TEXT NOT NULL DEFAULT 'baseline',
    status          TEXT NOT NULL DEFAULT 'queued',
    config_json     TEXT NOT NULL DEFAULT '{}',
    result_json     TEXT,
    error_msg       TEXT,
    created_at      REAL NOT NULL,
    started_at      REAL,
    completed_at    REAL
);

CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id      TEXT NOT NULL,
    sim_time_s  REAL NOT NULL,
    kpis_json   TEXT NOT NULL,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (sim_id) REFERENCES simulations(id)
);

CREATE TABLE IF NOT EXISTS agent_traces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id      TEXT NOT NULL,
    cycle_num   INTEGER NOT NULL,
    sim_time_s  REAL NOT NULL,
    trigger     TEXT NOT NULL DEFAULT 'auto',
    entries_json TEXT NOT NULL DEFAULT '[]',
    recorded_at REAL NOT NULL,
    FOREIGN KEY (sim_id) REFERENCES simulations(id)
);

CREATE TABLE IF NOT EXISTS shortcuts (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'prompt',
    description TEXT NOT NULL DEFAULT '',
    content     TEXT NOT NULL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS lean_kg_overrides (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    action      TEXT NOT NULL,
    data_json   TEXT NOT NULL,
    updated_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kpi_sim ON kpi_snapshots(sim_id);
CREATE INDEX IF NOT EXISTS idx_trace_sim ON agent_traces(sim_id);
"""


# ── Initialisation ────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create the database and all tables if they don't exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


# ── Settings CRUD ─────────────────────────────────────────────────────────────

async def get_setting(key: str, default: Any = None) -> Any:
    """Read one setting value (parsed from JSON)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return row[0]


async def set_setting(key: str, value: Any) -> None:
    """Write one setting value (serialised as JSON)."""
    serialised = json.dumps(value)
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, serialised, now),
        )
        await db.commit()


async def get_all_settings() -> Dict[str, Any]:
    """Return all settings as a dict."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
    result = {}
    for key, value in rows:
        try:
            result[key] = json.loads(value)
        except json.JSONDecodeError:
            result[key] = value
    return result


async def set_many_settings(updates: Dict[str, Any]) -> None:
    """Write multiple settings in one transaction."""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        for key, value in updates.items():
            await db.execute(
                "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value), now),
            )
        await db.commit()


# ── Simulations CRUD ──────────────────────────────────────────────────────────

async def upsert_simulation(
    sim_id: str,
    label: str = "",
    mode: str = "baseline",
    status: str = "queued",
    config: Optional[Dict] = None,
    result: Optional[Dict] = None,
    error_msg: Optional[str] = None,
    created_at: Optional[float] = None,
    started_at: Optional[float] = None,
    completed_at: Optional[float] = None,
) -> None:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO simulations
               (id,label,mode,status,config_json,result_json,error_msg,created_at,started_at,completed_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 label=excluded.label, mode=excluded.mode, status=excluded.status,
                 config_json=excluded.config_json, result_json=excluded.result_json,
                 error_msg=excluded.error_msg, started_at=excluded.started_at,
                 completed_at=excluded.completed_at
            """,
            (
                sim_id, label, mode, status,
                json.dumps(config or {}),
                json.dumps(result) if result else None,
                error_msg,
                created_at or now,
                started_at,
                completed_at,
            ),
        )
        await db.commit()


async def get_simulation(sim_id: str) -> Optional[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM simulations WHERE id=?", (sim_id,)) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    d = dict(row)
    d["config"] = json.loads(d.pop("config_json", "{}"))
    d["result"] = json.loads(d["result_json"]) if d.get("result_json") else None
    d.pop("result_json", None)
    return d


async def list_simulations(limit: int = 100) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM simulations ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cur:
            rows = await cur.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d.pop("config_json", "{}"))
        d["result"] = json.loads(d["result_json"]) if d.get("result_json") else None
        d.pop("result_json", None)
        result.append(d)
    return result


# ── KPI Snapshots ─────────────────────────────────────────────────────────────

async def insert_kpi_snapshot(sim_id: str, sim_time_s: float, kpis: Dict) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO kpi_snapshots(sim_id,sim_time_s,kpis_json,recorded_at) VALUES(?,?,?,?)",
            (sim_id, sim_time_s, json.dumps(kpis), time.time()),
        )
        await db.commit()


async def get_kpi_snapshots(sim_id: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT sim_time_s, kpis_json, recorded_at FROM kpi_snapshots WHERE sim_id=? ORDER BY sim_time_s",
            (sim_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"sim_time_s": r[0], "kpis": json.loads(r[1]), "recorded_at": r[2]} for r in rows]


# ── Agent Traces ──────────────────────────────────────────────────────────────

async def insert_agent_trace(
    sim_id: str, cycle_num: int, sim_time_s: float, trigger: str, entries: List
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO agent_traces(sim_id,cycle_num,sim_time_s,trigger,entries_json,recorded_at) VALUES(?,?,?,?,?,?)",
            (sim_id, cycle_num, sim_time_s, trigger, json.dumps(entries), time.time()),
        )
        await db.commit()


async def get_agent_traces(sim_id: str) -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT cycle_num,sim_time_s,trigger,entries_json,recorded_at FROM agent_traces WHERE sim_id=? ORDER BY cycle_num",
            (sim_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"cycle_num": r[0], "sim_time_s": r[1], "trigger": r[2],
         "entries": json.loads(r[3]), "recorded_at": r[4]}
        for r in rows
    ]


# ── Shortcuts CRUD ────────────────────────────────────────────────────────────

async def list_shortcuts() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM shortcuts ORDER BY category, name") as cur:
            rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def upsert_shortcut(shortcut_id: str, name: str, category: str, description: str, content: str) -> None:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO shortcuts(id,name,category,description,content,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, category=excluded.category,
                 description=excluded.description, content=excluded.content,
                 updated_at=excluded.updated_at""",
            (shortcut_id, name, category, description, content, now, now),
        )
        await db.commit()


async def delete_shortcut(shortcut_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM shortcuts WHERE id=?", (shortcut_id,))
        await db.commit()


# ── Lean KG Overrides ─────────────────────────────────────────────────────────

async def list_lean_overrides() -> List[Dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM lean_kg_overrides ORDER BY updated_at") as cur:
            rows = await cur.fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["data"] = json.loads(d.pop("data_json"))
        result.append(d)
    return result


async def upsert_lean_override(override_id: str, type_: str, action: str, data: Dict) -> None:
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO lean_kg_overrides(id,type,action,data_json,updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 type=excluded.type, action=excluded.action,
                 data_json=excluded.data_json, updated_at=excluded.updated_at""",
            (override_id, type_, action, json.dumps(data), now),
        )
        await db.commit()


async def delete_lean_override(override_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM lean_kg_overrides WHERE id=?", (override_id,))
        await db.commit()
