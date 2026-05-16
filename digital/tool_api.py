from typing import Dict, List, Any, Optional
import numpy as np

from magi.physical.constants import PHYSIO_CTRL_HR
from magi.digital.twin import DigitalTwin
from magi.digital.models import PhysioRecord

#  SECTION 9 — TOOL API  (Cognitive Layer interface)
#              All methods return JSON-serialisable dicts for LLM consumption.
# ─────────────────────────────────────────────────────────────────────────────

class ToolAPI:
    """
    Clean interface between the Digital Twin (Layer 3) and the Cognitive Layer
    (Layer 4). All methods correspond to named tools registered in the LLM
    agent's tool registry.

    Each method:
    1. Performs input validation and range-checking.
    2. Applies the change to the DT's ConfigState (thread-safe).
    3. Returns a structured dict that the LLM can parse for reasoning.

    Cognitive Layer integration example (Gemini tool calling):
        {
          "name": "set_robot_speed_factor",
          "parameters": {"factor": 1.15}
        }
        → api.set_robot_speed_factor(1.15)
        → {"success": True, "previous": 1.0, "new": 1.15, "effect_note": "..."}
    """

    def __init__(self, digital_twin: DigitalTwin):
        self.dt = digital_twin

    # ── Tool 1: get_current_kpis ──────────────────────────────────────

    def get_current_kpis(self) -> Dict[str, Any]:
        """
        Return KPIs from the most recent simulation run.

        Cognitive Layer usage: Called at each reasoning cycle to assess the
        current state of the production system.

        Returns:
            Dict containing all operational, physiological, and Lean KPIs,
            plus the current configuration snapshot.
        """
        result = self.dt.get_last_result()
        if result is None:
            return {"error": "No simulation has been run yet. Call run_simulation first."}
        return {
            "kpis":   result.kpis,
            "config": result.config_snapshot,
            "seed":   result.seed,
            "duration_hours": result.duration_hours,
        }

    # ── Tool 2: run_simulation ────────────────────────────────────────

    def run_simulation(
        self,
        duration_hours: float = 8.0,
        seed:           int   = 42,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute one simulation run, optionally overriding configuration.

        This is the primary tool for the Cognitive Layer to trigger a
        simulation with a specific parameter combination and retrieve KPIs.

        Args:
            duration_hours:   Simulated shift length.
            seed:             Random seed (use different seeds for replications).
            config_overrides: Dict of ConfigState parameter overrides to apply
                              before running (e.g., {"robot_speed_factor": 1.2}).

        Returns:
            KPI summary dict plus configuration and run metadata.
        """
        if config_overrides:
            try:
                self.dt.config.update(**config_overrides)
            except ValueError as e:
                return {"error": str(e)}

        t0     = time.perf_counter()
        result = self.dt.run(duration_hours=duration_hours, seed=seed)
        elapsed= time.perf_counter() - t0

        return {
            "kpis":           result.kpis,
            "config":         result.config_snapshot,
            "run_time_s":     round(elapsed, 3),
            "seed":           seed,
            "duration_hours": duration_hours,
        }

    # ── Tool 3: set_robot_speed_factor ───────────────────────────────

    def set_robot_speed_factor(self, factor: float) -> Dict[str, Any]:
        """
        Adjust the robot speed factor (affects all robot phase durations).

        Args:
            factor: Multiplier ∈ [0.5, 2.0]. 1.0 = baseline. 1.2 = 20% faster.

        Returns:
            Dict with previous value, new value, and expected ergonomic effect.

        Cognitive Layer notes:
        - Increasing this above 1.0 shortens robot phases → CW cycle is denser
          → human recovery windows shrink → PLI increases.
        - The Lean benefit (throughput) must be weighed against the ergonomic
          cost (PLI, fatigue score). This is the central HRC trade-off.
        """
        if not (0.5 <= factor <= 2.0):
            return {"error": f"robot_speed_factor must be in [0.5, 2.0]. Got {factor}"}
        prev = self.dt.config.robot_speed_factor
        self.dt.config.update(robot_speed_factor=factor)
        effect = "faster robot → shorter recovery windows → higher PLI" if factor > prev \
                 else "slower robot → longer recovery windows → lower PLI"
        return {"success": True, "previous": prev, "new": factor, "effect_note": effect}

    # ── Tool 4: assign_workers ────────────────────────────────────────

    def assign_workers(
        self, cw_worker_id: str, mw_worker_id: str
    ) -> Dict[str, Any]:
        """
        Assign workers to workstations by worker ID.

        Changing worker assignments swaps the physiological profile used for
        all subsequent task-phase sampling. This models shift scheduling
        optimisation: assigning the lower-HR worker to the higher-demand station.

        Args:
            cw_worker_id: Worker ID for CW ("001"–"004").
            mw_worker_id: Worker ID for MW ("001"–"004").

        Returns:
            Dict with new assignment and physiological baseline comparison.
        """
        valid = {"001", "002", "003", "004"}
        if cw_worker_id not in valid or mw_worker_id not in valid:
            return {"error": f"Worker IDs must be in {valid}"}
        prev_cw = self.dt.config.cw_worker_id
        prev_mw = self.dt.config.mw_worker_id
        self.dt.config.update(cw_worker_id=cw_worker_id, mw_worker_id=mw_worker_id)

        # Provide physiological context to assist Cognitive Layer reasoning
        cw_ctrl = PHYSIO_CTRL_HR.get(cw_worker_id, 82.0)
        mw_ctrl = PHYSIO_CTRL_HR.get(mw_worker_id, 82.0)
        return {
            "success":     True,
            "cw_worker":   {"previous": prev_cw, "new": cw_worker_id,
                            "ctrl_hr_bpm": cw_ctrl},
            "mw_worker":   {"previous": prev_mw, "new": mw_worker_id,
                            "ctrl_hr_bpm": mw_ctrl},
            "note":        "Physiological profiles updated. Re-run simulation to see effect.",
        }

    # ── Tool 5: set_takt_time ─────────────────────────────────────────

    def set_takt_time(self, takt_seconds: float) -> Dict[str, Any]:
        """
        Set the takt time (product inter-arrival interval in seconds).

        In Lean manufacturing, takt time = Available_time / Customer_demand.
        Reducing takt time increases throughput demand and physiological load
        on the MW operator (pure human work scales linearly with pace).

        Args:
            takt_seconds: Target cycle time (seconds). Range: [20, 300].

        Returns:
            Dict with change details and theoretical throughput impact.
        """
        if not (20.0 <= takt_seconds <= 300.0):
            return {"error": f"takt_time_seconds must be in [20, 300]. Got {takt_seconds}"}
        prev = self.dt.config.takt_time_seconds
        self.dt.config.update(takt_time_seconds=takt_seconds)
        theoretical_tph = 3600.0 / takt_seconds
        return {
            "success":              True,
            "previous_takt_s":      prev,
            "new_takt_s":           takt_seconds,
            "theoretical_throughput_per_hour": round(theoretical_tph, 2),
        }

    # ── Tool 6: set_buffer_capacity ───────────────────────────────────

    def set_buffer_capacity(self, capacity: int) -> Dict[str, Any]:
        """
        Set the inter-station buffer capacity (number of units).

        Higher capacity smooths flow between CW and MW (reduces MW starvation)
        but increases WIP (Work In Progress) inventory and physical floor space.

        Args:
            capacity: Number of units [1, 20].

        Returns:
            Dict with change details and WIP/flow note.
        """
        if not (1 <= capacity <= 20):
            return {"error": f"buffer_capacity must be in [1, 20]. Got {capacity}"}
        prev = self.dt.config.buffer_capacity
        self.dt.config.update(buffer_capacity=capacity)
        wip_note = "higher WIP, better MW starvation protection" if capacity > prev \
                   else "lower WIP, tighter flow, risk of MW starvation"
        return {"success": True, "previous": prev, "new": capacity, "wip_note": wip_note}

    # ── Tool 7: get_config_snapshot ───────────────────────────────────

    def get_config_snapshot(self) -> Dict[str, Any]:
        """
        Return the current configuration without running a simulation.
        Useful for the Cognitive Layer to verify its last intervention.
        """
        return self.dt.config.snapshot()

    # ── Tool 8: compare_to_baseline ──────────────────────────────────

    def compare_to_baseline(
        self,
        baseline_kpis:  Dict[str, Any],
        current_kpis:   Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Compute percentage changes between baseline and current KPI set.

        Used by the Cognitive Layer to quantify the impact of its interventions
        and generate the comparison table for the thesis results section.

        Args:
            baseline_kpis: KPI dict from Mode A (no AI intervention) run.
            current_kpis:  KPI dict from Mode B (MAGI-enhanced) run.
                           If None, uses last simulation result.

        Returns:
            Dict of KPI → {"baseline": v, "current": v, "delta_pct": pct}
        """
        if current_kpis is None:
            result = self.dt.get_last_result()
            if result is None:
                return {"error": "No simulation result available."}
            current_kpis = result.kpis

        comparison = {}
        key_kpis = [
            "throughput_units_per_hour",
            "cw_mean_cycle_time_s",
            "mw_mean_cycle_time_s",
            "cw_utilisation_pct",
            "mw_utilisation_pct",
            "robot_utilisation_pct",
            "cw_mean_hr_bpm",
            "mw_mean_hr_bpm",
            "pli_cw",
            "pli_mw",
            "mean_fatigue_score",
            "oee",
            "line_balance_ratio",
            "takt_adherence",
        ]
        for k in key_kpis:
            base = baseline_kpis.get(k, 0.0)
            curr = current_kpis.get(k, 0.0)
            if base != 0:
                delta_pct = ((curr - base) / abs(base)) * 100.0
            else:
                delta_pct = float("inf") if curr != 0 else 0.0
            comparison[k] = {
                "baseline":  round(base, 3),
                "current":   round(curr, 3),
                "delta_pct": round(delta_pct, 2),
            }
        return comparison

    # ── Tool 9: get_physio_summary ────────────────────────────────────

    def get_physio_summary(
        self, last_n_records: int = 50
    ) -> Dict[str, Any]:
        """
        Return aggregated physiological statistics from the most recent
        simulation run. Used by the Cognitive Layer for fatigue monitoring.

        Args:
            last_n_records: Number of most recent PhysioRecords to aggregate.

        Returns:
            Dict with per-workstation HR, fatigue, IBI summaries.
        """
        result = self.dt.get_last_result()
        if result is None:
            return {"error": "No simulation data available."}
        log = result.physio_log
        recent = log[-last_n_records:] if log else []
        if not recent:
            return {"status": "no_data", "records": 0}

        def _agg(recs):
            if not recs:
                return {}
            return {
                "count":              len(recs),
                "worker_id":          recs[-1].worker_id,
                "mean_hr_bpm":        round(float(np.mean([r.hr_bpm for r in recs])), 2),
                "max_hr_bpm":         round(float(max(r.hr_bpm for r in recs)), 2),
                "mean_fatigue":       round(float(np.mean([r.fatigue_score for r in recs])), 4),
                "max_fatigue":        round(float(max(r.fatigue_score for r in recs)), 4),
                "mean_ibi_ms":        round(float(np.mean([r.ibi_ms for r in recs])), 1),
                "elapsed_minutes":    round(recs[-1].elapsed_minutes, 1),
                "latest_sim_time_s":  round(recs[-1].sim_time, 1),
            }

        cw = [r for r in recent if r.workstation == "CW"]
        mw = [r for r in recent if r.workstation == "MW"]
        return {
            "status": "ok",
            "total_physio_records": len(log),
            "window_size":          len(recent),
            "cw": _agg(cw),
            "mw": _agg(mw),
        }

    # ── Tool 10: get_live_physio_summary ──────────────────────────────

    def get_live_physio_summary(
        self, physio_log: List, last_n: int = 50
    ) -> Dict[str, Any]:
        """
        Compute physio summary from a LIVE physio_log reference (mid-run).
        Unlike get_physio_summary, this works during a real-time simulation.
        """
        recent = physio_log[-last_n:] if physio_log else []
        if not recent:
            return {"status": "no_data"}

        def _agg(recs):
            if not recs:
                return {}
            ctrl_hr = PHYSIO_CTRL_HR.get(recs[-1].worker_id, 82.0)
            return {
                "count":           len(recs),
                "worker_id":       recs[-1].worker_id,
                "mean_hr_bpm":     round(float(np.mean([r.hr_bpm for r in recs])), 2),
                "max_hr_bpm":      round(float(max(r.hr_bpm for r in recs)), 2),
                "ctrl_hr_bpm":     ctrl_hr,
                "hr_elevation_pct":round((float(np.mean([r.hr_bpm for r in recs])) - ctrl_hr) / ctrl_hr * 100, 2),
                "mean_fatigue":    round(float(np.mean([r.fatigue_score for r in recs])), 4),
                "max_fatigue":     round(float(max(r.fatigue_score for r in recs)), 4),
                "mean_ibi_ms":     round(float(np.mean([r.ibi_ms for r in recs])), 1),
                "elapsed_min":     round(recs[-1].elapsed_minutes, 1),
            }

        cw = [r for r in recent if r.workstation == "CW"]
        mw = [r for r in recent if r.workstation == "MW"]
        return {"status": "ok", "cw": _agg(cw), "mw": _agg(mw)}

    # ── Tool 11: set_simulation_speed ─────────────────────────────────

    def set_simulation_speed(self, factor: float) -> Dict[str, Any]:
        """
        Change the simulation speed factor at runtime.

        Args:
            factor: New speed factor. 1.0 = real-time. 120.0 = fast.

        Returns:
            Dict with previous and new speed factor.
        """
        if not (0.1 <= factor <= 10000.0):
            return {"error": f"Speed factor must be in [0.1, 10000]. Got {factor}"}
        prev = self.dt.config.simulation_speed_factor
        self.dt.config.update(simulation_speed_factor=factor)
        return {"success": True, "previous": prev, "new": factor}


# ─────────────────────────────────────────────────────────────────────────────
