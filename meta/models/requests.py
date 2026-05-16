"""
MAGI Meta Layer — Pydantic Request Models.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class StartSimulationRequest(BaseModel):
    label: str = Field(default="", description="Human-readable label for the simulation run")
    mode: str = Field(default="baseline", description="Mode of operation: 'baseline' or 'magi'")
    duration_hours: float = Field(default=8.0, description="Duration of the simulation shift in hours")
    seed: int = Field(default=0, description="Random seed for reproducibility")
    speed_factor: float = Field(default=1.0, description="Wall-clock acceleration factor (1.0 = real-time)")
    config_overrides: Optional[Dict[str, Any]] = Field(default=None, description="Optional overrides for ConfigState parameters")


class UpdateConfigRequest(BaseModel):
    updates: Dict[str, Any] = Field(..., description="Key-value pairs of ConfigState parameters to update")


class UpdateSettingsRequest(BaseModel):
    updates: Dict[str, Any] = Field(..., description="Key-value pairs of settings to update")
