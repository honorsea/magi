"""
MAGI Meta Layer — Pydantic Response Models.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class GenericResponse(BaseModel):
    status: str
    message: Optional[str] = None


class SimulationSessionResponse(BaseModel):
    id: str
    label: str
    mode: str
    status: str
    config: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error_msg: Optional[str]
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]


class StartSimulationResponse(BaseModel):
    sim_id: str
    status: str
    message: str


class ConfigStateResponse(BaseModel):
    config: Dict[str, Any]


class SettingsResponse(BaseModel):
    settings: Dict[str, Any]
