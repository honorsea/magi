"""
MAGI Meta Layer — Agent Router.

Endpoints for interacting with the Cognitive Agent (Layer 4):
  POST /api/agent/{sim_id}/message  — send user message to running agent
  GET  /api/agent/{sim_id}/trace    — get agent reasoning trace
  GET  /api/agent/{sim_id}/tools    — list available tools
  GET  /api/agent/models            — list available Google models
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from magi.meta.services.sim_manager import get_manager

router = APIRouter()


class AgentMessageRequest(BaseModel):
    message: str


class AgentMessageResponse(BaseModel):
    status: str
    message: str
    queued: bool = False


class TraceEntry(BaseModel):
    sim_time_s: float
    wall_time: str
    trigger: str
    user_message: Optional[str]
    agent_text: str
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    files_created: List[str]


@router.post("/{sim_id}/message", response_model=AgentMessageResponse)
async def send_agent_message(sim_id: str, req: AgentMessageRequest):
    """Queue a user message to the agent running in the specified simulation."""
    manager = get_manager()
    session = manager.get_session(sim_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if session.status not in ("running", "paused"):
        raise HTTPException(status_code=400, detail="Simulation is not active")

    queued = manager.send_agent_message(sim_id, req.message)
    if queued:
        return AgentMessageResponse(status="success", message="Message queued for agent", queued=True)
    raise HTTPException(status_code=500, detail="Failed to queue message")


@router.get("/{sim_id}/trace")
async def get_agent_trace(sim_id: str):
    """Get the full agent reasoning trace for a simulation."""
    from magi.meta.services import db as _db
    traces = await _db.get_agent_traces(sim_id)
    return {"sim_id": sim_id, "traces": traces}


@router.get("/{sim_id}/tools")
async def list_agent_tools(sim_id: str):
    """List the tools available to the Cognitive Agent."""
    return {
        "tools": [
            {"name": "get_current_kpis", "description": "Get all current KPIs from the simulation"},
            {"name": "set_robot_speed_factor", "description": "Set robot speed multiplier [0.5, 2.0]", "params": ["factor"]},
            {"name": "set_takt_time", "description": "Set product arrival interval in seconds [20, 300]", "params": ["takt_seconds"]},
            {"name": "assign_workers", "description": "Assign workers 001-004 to CW/MW stations", "params": ["cw_worker_id", "mw_worker_id"]},
            {"name": "set_buffer_capacity", "description": "Set buffer size [1, 20]", "params": ["capacity"]},
            {"name": "retrieve_lean_methods", "description": "Query the Lean KG for relevant methods", "params": ["query", "top_k"]},
            {"name": "get_lean_method_detail", "description": "Get full detail for a Lean method", "params": ["method_name"]},
            {"name": "execute_python_code", "description": "Run Python for analysis/optimisation/plots", "params": ["code"]},
            {"name": "log_intervention", "description": "Log a manual intervention decision", "params": ["description", "rationale"]},
        ]
    }


@router.get("/models")
async def list_models():
    """List available Google Gemini models."""
    return {
        "models": [
            {"id": "gemini-2.5-flash-preview-04-17", "name": "Gemini 2.5 Flash (recommended)", "tier": "fast"},
            {"id": "gemini-2.5-pro-preview-05-06",   "name": "Gemini 2.5 Pro (most capable)", "tier": "pro"},
            {"id": "gemini-2.0-flash",               "name": "Gemini 2.0 Flash", "tier": "fast"},
            {"id": "gemini-1.5-pro",                 "name": "Gemini 1.5 Pro", "tier": "pro"},
            {"id": "gemini-1.5-flash",               "name": "Gemini 1.5 Flash", "tier": "fast"},
        ]
    }
