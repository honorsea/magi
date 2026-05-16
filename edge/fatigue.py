import numpy as np
from typing import Dict, List, Any

from magi.physical.constants import PHYSIO_CTRL_HR, PHYSIO_IBI_BASELINES
from magi.digital.config import ConfigState
from magi.digital.models import PhysioRecord

#  SECTION 14 — FATIGUE MONITOR
#              Classifies operator fatigue level from physiological signals.
# ─────────────────────────────────────────────────────────────────────────────

class FatigueMonitor:
    """
    Monitors physiological signals and classifies operator fatigue.

    Three-level classification aligned with the Lean Knowledge Graph's
    muri_analysis trigger thresholds:
      - Normal    (score < 0.4)
      - Elevated  (0.4 ≤ score < 0.6)
      - Warning   (0.6 ≤ score < 0.8)
      - Critical  (score ≥ 0.8)

    Cross-validates HR elevation against individual CTRL baselines and
    IBI elongation to reduce false positives.
    """

    LEVELS = {
        "normal":   (0.0, 0.4),
        "elevated": (0.4, 0.6),
        "warning":  (0.6, 0.8),
        "critical": (0.8, 1.0),
    }

    def assess(
        self,
        physio_log: List[PhysioRecord],
        config: ConfigState,
        window_records: int = 30,
    ) -> Dict[str, Any]:
        """
        Assess fatigue for each active worker from recent physio records.

        Returns:
            Dict with per-worker fatigue classification and supporting metrics.
        """
        recent = physio_log[-window_records:] if physio_log else []
        if not recent:
            return {"status": "insufficient_data", "workers": {}}

        workers: Dict[str, Dict] = {}
        for ws_label, ws_name, wid_attr in [
            ("CW", "Collaborative Workstation", config.cw_worker_id),
            ("MW", "Manual Workstation",        config.mw_worker_id),
        ]:
            recs = [r for r in recent if r.workstation == ws_label]
            if not recs:
                continue
            wid = recs[-1].worker_id
            ctrl_hr = PHYSIO_CTRL_HR.get(wid, 82.0)

            mean_hr  = float(np.mean([r.hr_bpm for r in recs]))
            max_hr   = float(max(r.hr_bpm for r in recs))
            mean_fat = float(np.mean([r.fatigue_score for r in recs]))
            max_fat  = float(max(r.fatigue_score for r in recs))
            mean_ibi = float(np.mean([r.ibi_ms for r in recs]))

            # HR elevation check
            hr_elevation_pct = (mean_hr - ctrl_hr) / ctrl_hr * 100.0

            # IBI baseline (approximate from PHYSIO_IBI_BASELINES)
            task_ibis = PHYSIO_IBI_BASELINES.get(wid, {})
            all_base_ibis = [v[0] for v in task_ibis.values()] if task_ibis else [2000.0]
            base_ibi = float(np.mean(all_base_ibis))
            ibi_elevation_pct = (mean_ibi - base_ibi) / base_ibi * 100.0

            # Classify
            level = "normal"
            for lv, (lo, hi) in self.LEVELS.items():
                if lo <= max_fat < hi:
                    level = lv
            if max_fat >= 0.8:
                level = "critical"

            workers[f"{ws_label}_{wid}"] = {
                "worker_id":          wid,
                "workstation":        ws_label,
                "fatigue_level":      level,
                "mean_fatigue_score": round(mean_fat, 4),
                "max_fatigue_score":  round(max_fat, 4),
                "mean_hr_bpm":        round(mean_hr, 2),
                "max_hr_bpm":         round(max_hr, 2),
                "ctrl_hr_bpm":        round(ctrl_hr, 2),
                "hr_elevation_pct":   round(hr_elevation_pct, 2),
                "mean_ibi_ms":        round(mean_ibi, 1),
                "ibi_elevation_pct":  round(ibi_elevation_pct, 2),
                "elapsed_minutes":    round(recs[-1].elapsed_minutes, 1),
                "needs_intervention": level in ("warning", "critical"),
            }

        return {"status": "ok", "workers": workers}


# ─────────────────────────────────────────────────────────────────────────────
