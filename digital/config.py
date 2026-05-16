import threading
from dataclasses import dataclass, field
from typing import Dict, Any

#  SECTION 3 — CONFIGURATION STATE (thread-safe, AI-modifiable at runtime)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConfigState:
    """
    Encapsulates all tunable simulation parameters.

    This class is the single point of configuration for the Digital Twin.
    The Cognitive Layer (Layer 4) modifies parameters by calling the
    Tool API, which updates this object under a reentrant lock to ensure
    thread-safe access during live simulation runs.

    Parameters
    ----------
    cw_worker_id : str
        Worker assigned to the Collaborative Workstation ("001"–"004").
    mw_worker_id : str
        Worker assigned to the Manual Workstation ("001"–"004").
    robot_speed_factor : float
        Multiplier applied to all deterministic robot phase durations.
        1.0 = baseline speed. 1.2 = robot runs 20% faster (shorter cycle).
    takt_time_seconds : float
        Target cycle time (seconds) driving product arrival into the line.
        Lower takt = higher production pace (Lean target rate).
    buffer_capacity : int
        Maximum number of units that can queue in the CW→MW inter-station
        buffer. Finite capacity models real physical space constraints.
    simulation_speed_factor : float
        Ratio of simulated seconds per real second. 1.0 = real-time.
        60.0 = one simulated hour runs in one real minute (used for experiments).
    inter_arrival_jitter_cv : float
        Coefficient of variation applied as Normal noise to takt arrivals.
        Models non-uniform conveyor pacing (CV=0 → deterministic arrivals).
    """
    cw_worker_id:           str   = "001"
    mw_worker_id:           str   = "001"
    robot_speed_factor:     float = 1.0
    takt_time_seconds:      float = 60.0
    buffer_capacity:        int   = 5
    simulation_speed_factor:float = 1.0    # 1.0 = real-time; 60.0 = 1 sim-min per real-sec
    inter_arrival_jitter_cv:float = 0.05

    # Internal RLock — guards concurrent read/write from cognitive layer thread.
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def update(self, **kwargs) -> None:
        """Thread-safe parameter update. Accepts any attribute by keyword."""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self, key) and not key.startswith("_"):
                    setattr(self, key, value)
                else:
                    raise ValueError(f"ConfigState has no parameter '{key}'")

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable copy of current configuration."""
        with self._lock:
            return {
                "cw_worker_id": self.cw_worker_id,
                "mw_worker_id": self.mw_worker_id,
                "robot_speed_factor": self.robot_speed_factor,
                "takt_time_seconds": self.takt_time_seconds,
                "buffer_capacity": self.buffer_capacity,
                "simulation_speed_factor": self.simulation_speed_factor,
                "inter_arrival_jitter_cv": self.inter_arrival_jitter_cv,
            }

    def to_dict(self) -> Dict[str, Any]:
        """Alias for snapshot() — JSON-serialisable copy of current configuration."""
        return self.snapshot()


# ─────────────────────────────────────────────────────────────────────────────
