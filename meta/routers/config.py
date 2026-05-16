"""
MAGI Meta Layer — Config Router.
"""

from fastapi import APIRouter, HTTPException

from magi.meta.models.requests import UpdateConfigRequest, UpdateSettingsRequest
from magi.meta.models.responses import GenericResponse, ConfigStateResponse, SettingsResponse
from magi.meta.services import settings_store
from magi.meta.services.sim_manager import get_manager

router = APIRouter()


@router.get("/settings", response_model=SettingsResponse)
async def get_all_settings():
    """Get all dashboard settings."""
    settings = await settings_store.get_all()
    return SettingsResponse(settings=settings)


@router.put("/settings", response_model=GenericResponse)
async def update_settings(req: UpdateSettingsRequest):
    """Update one or more dashboard settings."""
    try:
        await settings_store.set_many(req.updates)
        return GenericResponse(status="success", message="Settings updated")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/settings/reset", response_model=GenericResponse)
async def reset_settings():
    """Reset all settings to defaults."""
    await settings_store.reset_to_defaults()
    return GenericResponse(status="success", message="Settings reset to defaults")


@router.get("/{sim_id}/config", response_model=ConfigStateResponse)
async def get_simulation_config(sim_id: str):
    """Get the live ConfigState of a running simulation."""
    manager = get_manager()
    session = manager.get_session(sim_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return ConfigStateResponse(config=session.config.to_dict())


@router.put("/{sim_id}/config", response_model=GenericResponse)
async def update_simulation_config(sim_id: str, req: UpdateConfigRequest):
    """Update the live ConfigState of a running simulation (Cognitive Layer hook)."""
    manager = get_manager()
    session = manager.get_session(sim_id)
    if not session:
        raise HTTPException(status_code=404, detail="Simulation not found")
    
    try:
        session.config.update(**req.updates)
        return GenericResponse(status="success", message="Configuration updated")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
