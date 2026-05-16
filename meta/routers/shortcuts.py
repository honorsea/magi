"""
MAGI Meta Layer — Shortcuts Router.

CRUD for user-defined prompt templates and analysis presets stored in SQLite.
"""

import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from magi.meta.services import db as _db

router = APIRouter()


class ShortcutCreate(BaseModel):
    name: str
    category: str = "prompt"   # "prompt" | "analysis" | "lean"
    description: str = ""
    content: str


class ShortcutResponse(BaseModel):
    id: str
    name: str
    category: str
    description: str
    content: str
    created_at: float
    updated_at: float


@router.get("/", response_model=List[ShortcutResponse])
async def list_shortcuts():
    return await _db.list_shortcuts()


@router.post("/", response_model=ShortcutResponse)
async def create_shortcut(req: ShortcutCreate):
    sc_id = str(uuid.uuid4())[:12]
    now = time.time()
    await _db.upsert_shortcut(sc_id, req.name, req.category, req.description, req.content)
    return ShortcutResponse(id=sc_id, name=req.name, category=req.category,
                            description=req.description, content=req.content,
                            created_at=now, updated_at=now)


@router.put("/{shortcut_id}", response_model=ShortcutResponse)
async def update_shortcut(shortcut_id: str, req: ShortcutCreate):
    now = time.time()
    await _db.upsert_shortcut(shortcut_id, req.name, req.category, req.description, req.content)
    return ShortcutResponse(id=shortcut_id, name=req.name, category=req.category,
                            description=req.description, content=req.content,
                            created_at=now, updated_at=now)


@router.delete("/{shortcut_id}")
async def delete_shortcut(shortcut_id: str):
    await _db.delete_shortcut(shortcut_id)
    return {"status": "success", "message": "Shortcut deleted"}


# ── Seed default shortcuts ────────────────────────────────────────────────────

_DEFAULT_SHORTCUTS = [
    {
        "name": "Check Worker Fatigue",
        "category": "prompt",
        "description": "Quick ergonomics assessment",
        "content": "Analyse current worker fatigue levels for both CW and MW. Are any thresholds being breached? What immediate actions do you recommend?"
    },
    {
        "name": "Bottleneck Analysis",
        "category": "analysis",
        "description": "Identify the current production bottleneck",
        "content": "Perform a bottleneck analysis using current KPIs. Which station (CW or MW) is the constraint? Calculate the line balance ratio and recommend a corrective action."
    },
    {
        "name": "Optimise Robot Speed",
        "category": "lean",
        "description": "Find optimal robot speed for throughput vs ergonomics",
        "content": "What is the optimal robot speed factor that maximises throughput while keeping CW worker fatigue below 0.6? Use a systematic approach and apply the change."
    },
    {
        "name": "Muri (Overburden) Check",
        "category": "lean",
        "description": "Identify overburden waste",
        "content": "Assess the current simulation for Muri (overburden). Which workers or processes are overloaded? Reference the Lean KG for applicable countermeasures."
    },
    {
        "name": "KPI Summary",
        "category": "prompt",
        "description": "Get a full KPI summary table",
        "content": "Give me a complete summary of all current KPIs — operational, physiological, and Lean metrics — formatted as a clear table."
    },
]


@router.post("/seed-defaults")
async def seed_default_shortcuts():
    """Seed the database with useful default shortcuts if not already present."""
    existing = await _db.list_shortcuts()
    existing_names = {s["name"] for s in existing}
    added = 0
    for sc in _DEFAULT_SHORTCUTS:
        if sc["name"] not in existing_names:
            sc_id = str(uuid.uuid4())[:12]
            await _db.upsert_shortcut(sc_id, sc["name"], sc["category"], sc["description"], sc["content"])
            added += 1
    return {"status": "success", "added": added}
