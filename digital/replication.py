import pandas as pd
import numpy as np
import scipy.stats as st
import time
from typing import Dict, Any

from magi.digital.twin import DigitalTwin

#  SECTION 10 — REPLICATION RUNNER (Statistical Experiment Infrastructure)
# ─────────────────────────────────────────────────────────────────────────────

class ReplicationRunner:
    """
    Runs multiple independent replications of the simulation for
    statistically valid experimental comparison (Mode A vs Mode B).

    Each replication uses a different random seed (seed = base_seed + i)
    ensuring independence while maintaining reproducibility. This follows
    the standard independent replications method (Law, 2015, Simulation
    Modeling and Analysis, 5th ed., McGraw-Hill).

    The runner produces a DataFrame of KPIs across all replications,
    from which confidence intervals and significance tests are computed.
    """

    def __init__(self, digital_twin: DigitalTwin):
        self.dt = digital_twin

    def run_replications(
        self,
        n:              int   = 30,
        duration_hours: float = 8.0,
        base_seed:      int   = 0,
        label:          str   = "experiment",
        verbose:        bool  = True,
    ) -> pd.DataFrame:
        """
        Execute n independent replications and return aggregated KPI DataFrame.

        Args:
            n:              Number of replications (30 is conventional for
                            95% CI width ≤ 0.5 standard error).
            duration_hours: Simulated shift length per replication.
            base_seed:      Seeds run from base_seed to base_seed + n - 1.
            label:          Label column added to output (e.g. "baseline", "magi").
            verbose:        Print progress to console.

        Returns:
            pd.DataFrame with one row per replication, columns = KPI names + metadata.
        """
        records = []
        t_total = time.perf_counter()

        for i in range(n):
            seed = base_seed + i
            if verbose and (i % 5 == 0):
                print(f"[ReplicationRunner] Running replication {i+1}/{n} (seed={seed}) ...")
            result = self.dt.run(duration_hours=duration_hours, seed=seed)
            row    = {"replication": i + 1, "seed": seed, "label": label}
            row.update(result.kpis)
            records.append(row)

        df = pd.DataFrame(records)
        elapsed = time.perf_counter() - t_total

        if verbose:
            print(f"\n[ReplicationRunner] Completed {n} replications in {elapsed:.1f}s.")
            print(self._summary_stats(df, label))

        return df

    @staticmethod
    def _summary_stats(df: pd.DataFrame, label: str) -> str:
        """Format mean ± 95% CI for key KPIs."""
        key_kpis = [
            "throughput_units_per_hour", "cw_mean_hr_bpm", "mw_mean_hr_bpm",
            "pli_cw", "pli_mw", "oee", "mean_fatigue_score",
        ]
        lines = [f"\n  === {label.upper()} — Replication Summary (mean ± 95% CI) ==="]
        n = len(df)
        for k in key_kpis:
            if k not in df.columns:
                continue
            mu  = df[k].mean()
            sem = df[k].std() / (n ** 0.5)
            ci  = 1.96 * sem
            lines.append(f"  {k:40s}: {mu:.3f} ± {ci:.3f}")
        return "\n".join(lines)

    @staticmethod
    def compute_paired_comparison(
        baseline_df: pd.DataFrame,
        magi_df:     pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Compute paired t-test comparisons between baseline and MAGI replications.

        Appropriate because both modes use the same seed sequence (paired design),
        ensuring that random variation cancels and only the AI intervention's
        effect remains. Reference: Law (2015), Section 10.3.

        Args:
            baseline_df: KPI DataFrame from Mode A (n replications).
            magi_df:     KPI DataFrame from Mode B (n replications).

        Returns:
            DataFrame with columns: kpi, baseline_mean, magi_mean,
            delta, delta_pct, t_stat, p_value, significant_05.
        """
        from scipy.stats import ttest_rel

        key_kpis = [
            "throughput_units_per_hour",
            "cw_mean_cycle_time_s", "mw_mean_cycle_time_s",
            "cw_utilisation_pct", "mw_utilisation_pct",
            "cw_mean_hr_bpm", "mw_mean_hr_bpm",
            "pli_cw", "pli_mw",
            "mean_fatigue_score", "peak_fatigue_score",
            "oee", "line_balance_ratio", "takt_adherence",
        ]
        rows = []
        for k in key_kpis:
            if k not in baseline_df.columns or k not in magi_df.columns:
                continue
            base_vals = baseline_df[k].values
            magi_vals = magi_df[k].values
            t_stat, p_val = ttest_rel(base_vals, magi_vals)
            base_mean = float(np.mean(base_vals))
            magi_mean = float(np.mean(magi_vals))
            delta     = magi_mean - base_mean
            delta_pct = (delta / abs(base_mean) * 100) if base_mean != 0 else float("nan")
            rows.append({
                "kpi":             k,
                "baseline_mean":   round(base_mean, 4),
                "magi_mean":       round(magi_mean, 4),
                "delta":           round(delta, 4),
                "delta_pct":       round(delta_pct, 2),
                "t_stat":          round(float(t_stat), 4),
                "p_value":         round(float(p_val), 6),
                "significant_05":  bool(p_val < 0.05),
            })
        return pd.DataFrame(rows)



# ─────────────────────────────────────────────────────────────────────────────
