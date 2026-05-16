import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

#  SECTION 5 — PHYSIOLOGICAL SAMPLER
#              Three-component model: Empirical Baseline + Workload Delta
#              + Fatigue Overlay (after Åstrand & Rodahl, 1986; Kroemer &
#              Grandjean, 1997 for linear workload-HR relationship in
#              moderate-effort assembly tasks).
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PhysioRecord:
    """
    A single physiological observation emitted per task-phase execution.

    This record is the atomic unit of data flowing from the Digital Twin
    to the Physical Layer (Layer 1) and subsequently to the Edge Layer
    (Layer 2) for fatigue classification.

    Attributes
    ----------
    sim_time       : Simulation clock time at observation (seconds).
    elapsed_minutes: Cumulative worked time this worker has spent in the
                     simulation (minutes), used by the fatigue overlay.
    worker_id      : Worker whose profile generated this record.
    workstation    : "CW" or "MW".
    task_label     : Task phase label (e.g., "02_visual_check").
    hr_bpm         : Estimated heart rate (BPM) = baseline + delta + fatigue.
    rr_interval_ms : Estimated R-R interval (ms) = 60,000 / hr_bpm.
    ibi_ms         : Inter-blink interval (ms) = baseline + fatigue overlay.
    hr_baseline    : Empirical HR baseline for this (worker, task) cell.
    hr_delta       : Workload delta component (from config change).
    hr_fatigue     : Fatigue overlay contribution (ms into shift).
    fatigue_score  : Normalised fatigue index [0–1] at this moment.
    phase_duration : Actual sampled duration of this phase (seconds).
    product_id     : Unit identifier currently being processed.
    """
    sim_time:        float
    elapsed_minutes: float
    worker_id:       str
    workstation:     str
    task_label:      str
    hr_bpm:          float
    rr_interval_ms:  float
    ibi_ms:          float
    hr_baseline:     float
    hr_delta:        float
    hr_fatigue:      float
    fatigue_score:   float
    phase_duration:  float
    product_id:      int


#  SECTION 6 — TASK & KPI RECORD DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TaskRecord:
    """
    Logged at completion of each individual task phase (CW) or full cycle (MW).
    Provides the raw event log from which all KPIs are computed post-hoc.
    """
    product_id:       int
    workstation:      str       # "CW" or "MW"
    task_label:       str
    worker_id:        str
    phase_start_time: float     # simulation clock (seconds)
    phase_end_time:   float
    phase_duration:   float
    is_robot_phase:   bool
    queue_wait_time:  float     # wait in buffer before this task started
    physio:           Optional[PhysioRecord] = None


@dataclass
class SimulationResult:
    """
    Complete output of one simulation replication (a single `dt.run()` call).
    Contains raw event logs, KPI summaries, and configuration metadata.
    """
    config_snapshot:   Dict[str, Any]
    seed:              int
    duration_hours:    float
    task_log:          List[TaskRecord]
    physio_log:        List[PhysioRecord]
    kpis:              Dict[str, Any]
    run_timestamp:     str = field(default_factory=lambda: pd.Timestamp.now().isoformat())

    def to_dataframe(self) -> pd.DataFrame:
        """Export task log as a flat DataFrame for statistical analysis."""
        records = []
        for tr in self.task_log:
            row = {
                "product_id":       tr.product_id,
                "workstation":      tr.workstation,
                "task_label":       tr.task_label,
                "worker_id":        tr.worker_id,
                "phase_start":      tr.phase_start_time,
                "phase_end":        tr.phase_end_time,
                "phase_duration":   tr.phase_duration,
                "is_robot_phase":   tr.is_robot_phase,
                "queue_wait":       tr.queue_wait_time,
            }
            if tr.physio:
                row.update({
                    "hr_bpm":           tr.physio.hr_bpm,
                    "rr_ms":            tr.physio.rr_interval_ms,
                    "ibi_ms":           tr.physio.ibi_ms,
                    "hr_baseline":      tr.physio.hr_baseline,
                    "hr_delta":         tr.physio.hr_delta,
                    "hr_fatigue":       tr.physio.hr_fatigue,
                    "fatigue_score":    tr.physio.fatigue_score,
                    "elapsed_min":      tr.physio.elapsed_minutes,
                })
            records.append(row)
        return pd.DataFrame(records)

    def summary(self) -> str:
        """Return a formatted KPI summary string."""
        k   = self.kpis
        sep = "-" * 60
        lines = [
            sep,
            "  MAGI DIGITAL TWIN — SIMULATION RESULT SUMMARY",
            sep,
            f"  Config     : {self.config_snapshot}",
            f"  Seed       : {self.seed}  |  Duration: {self.duration_hours:.1f} h",
            sep,
            "  OPERATIONAL KPIs",
            f"    Throughput            : {k.get('throughput_units_per_hour', 0):.2f} units/hr",
            f"    Units produced        : {k.get('total_units_produced', 0)}",
            f"    CW cycle time (mean)  : {k.get('cw_mean_cycle_time_s', 0):.1f} s",
            f"    MW cycle time (mean)  : {k.get('mw_mean_cycle_time_s', 0):.1f} s",
            f"    CW utilisation        : {k.get('cw_utilisation_pct', 0):.1f}%",
            f"    MW utilisation        : {k.get('mw_utilisation_pct', 0):.1f}%",
            f"    Robot utilisation     : {k.get('robot_utilisation_pct', 0):.1f}%",
            f"    Mean buffer wait (CW→MW): {k.get('mean_buffer_wait_s', 0):.2f} s",
            sep,
            "  PHYSIOLOGICAL / ERGONOMIC KPIs",
            f"    CW worker mean HR     : {k.get('cw_mean_hr_bpm', 0):.1f} BPM",
            f"    CW worker peak HR     : {k.get('cw_peak_hr_bpm', 0):.1f} BPM",
            f"    MW worker mean HR     : {k.get('mw_mean_hr_bpm', 0):.1f} BPM",
            f"    MW worker peak HR     : {k.get('mw_peak_hr_bpm', 0):.1f} BPM",
            f"    PLI (CW)              : {k.get('pli_cw', 0):.2f} BPM·min",
            f"    PLI (MW)              : {k.get('pli_mw', 0):.2f} BPM·min",
            f"    Mean fatigue score    : {k.get('mean_fatigue_score', 0):.3f}",
            f"    Peak fatigue score    : {k.get('peak_fatigue_score', 0):.3f}",
            sep,
            "  LEAN KPIs",
            f"    OEE (proxy)           : {k.get('oee', 0):.3f}",
            f"    Line balance ratio    : {k.get('line_balance_ratio', 0):.3f}",
            f"    Takt adherence        : {k.get('takt_adherence', 0):.3f}",
            f"    CW idle fraction      : {k.get('cw_idle_fraction', 0):.3f}",
            sep,
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
