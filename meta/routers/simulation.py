"""
MAGI Meta Layer — Simulation Router.
"""

from typing import List

from fastapi import APIRouter, HTTPException

from magi.meta.models.requests import StartSimulationRequest
from magi.meta.models.responses import GenericResponse, SimulationSessionResponse, StartSimulationResponse
from magi.meta.services.sim_manager import get_manager

router = APIRouter()


@router.post("/run", response_model=StartSimulationResponse)
async def start_simulation(req: StartSimulationRequest):
    """Start a new simulation session."""
    manager = get_manager()
    try:
        sim_id = await manager.start_simulation(
            label=req.label,
            mode=req.mode,
            duration_hours=req.duration_hours,
            seed=req.seed,
            config_overrides=req.config_overrides,
            speed_factor=req.speed_factor,
        )
        return StartSimulationResponse(sim_id=sim_id, status="success", message="Simulation started")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=List[SimulationSessionResponse])
async def list_sessions():
    """List all simulation sessions (running, paused, completed, etc.)."""
    manager = get_manager()
    return manager.list_sessions()


@router.get("/{sim_id}", response_model=SimulationSessionResponse)
async def get_session(sim_id: str):
    """Get details of a specific simulation session."""
    manager = get_manager()
    session = manager.get_session(sim_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return session.to_dict()


@router.post("/{sim_id}/pause", response_model=GenericResponse)
async def pause_simulation(sim_id: str):
    """Pause a running simulation."""
    manager = get_manager()
    if manager.pause_simulation(sim_id):
        return GenericResponse(status="success", message="Simulation paused")
    raise HTTPException(status_code=400, detail="Could not pause simulation")


@router.post("/{sim_id}/resume", response_model=GenericResponse)
async def resume_simulation(sim_id: str):
    """Resume a paused simulation."""
    manager = get_manager()
    if manager.resume_simulation(sim_id):
        return GenericResponse(status="success", message="Simulation resumed")
    raise HTTPException(status_code=400, detail="Could not resume simulation")


@router.post("/{sim_id}/stop", response_model=GenericResponse)
async def stop_simulation(sim_id: str):
    """Stop a simulation."""
    manager = get_manager()
    if manager.stop_simulation(sim_id):
        return GenericResponse(status="success", message="Simulation stopped")
    raise HTTPException(status_code=400, detail="Could not stop simulation")


@router.delete("/{sim_id}", response_model=GenericResponse)
async def delete_simulation(sim_id: str):
    """Delete a simulation session."""
    manager = get_manager()
    if manager.delete_session(sim_id):
        return GenericResponse(status="success", message="Simulation deleted")
    raise HTTPException(status_code=404, detail="Simulation not found")
