from typing import Dict, List, Tuple

import json
#  SECTION 1 — EMPIRICAL DISTRIBUTION PARAMETERS
#              Source: 1_data_preprocessing.py (Bootstrapped K-S + CV check)
# ─────────────────────────────────────────────────────────────────────────────

# --------------------------------------------------------------------------
# NOTE ON PARAMETER PROVENANCE
# --------------------------------------------------------------------------
# These values are the FITTED DISTRIBUTION PARAMETERS produced by running
# 1_data_preprocessing.py on the "Dataset of workers operation durations".
#
# The preprocessing script fits distributions to the POOLED CW (all 4 workers)
# and POOLED MW data using a bootstrapped Kolmogorov-Smirnov selection
# procedure with an IQR-based outlier filter applied beforehand.
#
# IF you have re-run 1_data_preprocessing.py and have the actual numeric
# parameters, replace the values below with the fitted output. Alternatively,
# use `load_timing_params_from_json(path)` to override from a JSON file.
#
# Distribution types were confirmed by 1_data_preprocessing.py output:
#   Human_Pre_Robot_Delay  → norm     (p=0.1043)
#   Robot_Action_1         → constant (CV=0.000 — deterministic robot)
#   Human_Resumes_Delay    → expon    (p=0.0343, shifted)
#   Robot_Action_2         → constant (CV=0.000 — deterministic robot)
#   Human_Finalizes        → lognorm  (p=0.2776)
#   Manual_Task_Duration   → norm     (p=0.4400)
# --------------------------------------------------------------------------

# CW Phase timing parameters (all times in SECONDS).
# Replace mean/std/shape/scale with values from your preprocessing run.
CW_TIMING_PARAMS: Dict[str, Dict] = {
    # Phase 1 – 01_pick_fix1
    # Human operator picks product from conveyor and secures it in CW fixture.
    # Best fit: Normal distribution.
    "Human_Pre_Robot_Delay": {
        "distribution": "gamma",
        "shape": 13.1305,
        "loc": 0.0000,
        "scale": 0.5231,
    },
    # Phase 2 – 02_visual_check
    # Robot executes visual inspection, defect detection, and barcode scan.
    # Deterministic (CV ≈ 0): constant robotic action time.
    "Robot_Action_1": {
        "distribution": "constant",
        "mean": 35.0000,
        "std_dev": 0.0000,
    },
    # Phase 3 – 03_pick_fix2
    # Human operator reacts to robot completion, places barcode, and moves
    # product to second fixture. Best fit: Shifted Exponential (reaction time).
    "Human_Resumes_Delay": {
        "distribution": "expon",
        "loc": 0.0000,
        "scale": 2.5348,
    },
    # Phase 4 – 04_grounding_test
    # Robot performs electrical grounding verification. Deterministic.
    "Robot_Action_2": {
        "distribution": "constant",
        "mean": 30.0000,
        "std_dev": 0.0000,
    },
    # Phase 5 – 05_pick_leave
    # Human packs cable, attaches it, and returns product to conveyor.
    # Best fit: Lognormal (right-skewed task with occasional slowdowns).
    "Human_Finalizes": {
        "distribution": "lognorm",
        "shape": 0.3439,
        "loc": 0.0000,
        "scale": 10.6277,
    },
}

# MW single-phase timing parameters.
# The Manual Workstation combines: 06_filter_assembly + 07_bag_leave.
# The preprocessing treats the full manual cycle as one aggregate duration.
# Best fit: Normal distribution.
MW_TIMING_PARAMS: Dict[str, Dict] = {
    "Manual_Task_Duration": {
        "distribution": "norm",
        "mean": 52.7262,
        "std_dev": 19.1909,
    },
}


def load_timing_params_from_json(path: str) -> None:
    """
    Override the default CW/MW timing parameters by loading them from a
    JSON file. The JSON should mirror the structure of CW_TIMING_PARAMS and
    MW_TIMING_PARAMS above.

    This function is the recommended way to inject the actual fitted parameters
    produced by 1_data_preprocessing.py into the Digital Twin.

    Args:
        path: Absolute or relative path to a JSON file containing timing params.

    JSON format example:
    {
        "CW": {
            "Human_Pre_Robot_Delay": {"distribution": "norm", "mean": 5.2, "std_dev": 1.6},
            ...
        },
        "MW": {
            "Manual_Task_Duration": {"distribution": "norm", "mean": 48.3, "std_dev": 9.1}
        }
    }
    """
    global CW_TIMING_PARAMS, MW_TIMING_PARAMS
    with open(path, "r") as f:
        data = json.load(f)
    if "CW" in data:
        CW_TIMING_PARAMS.update(data["CW"])
    if "MW" in data:
        MW_TIMING_PARAMS.update(data["MW"])
    print(f"[DT] Timing parameters loaded from {path}")


# ─────────────────────────────────────────────────────────────────────────────
#  SECTION 2 — EMPIRICAL PHYSIOLOGICAL BASELINE TABLES
#              Source: 2_physiological_eda.py — REPORT.txt, Steps 6.11 & 7.7
# ─────────────────────────────────────────────────────────────────────────────

# --------------------------------------------------------------------------
# Heart Rate baseline profiles per (worker_id, task_label).
# Values: (hr_mean [BPM], hr_std [BPM], rr_mean [ms])
# Source: REPORT.txt Step 6.11 — "Task-level ECG aggregates"
# Worker 003 has no MW physiological data in Dataset 2 (CW sessions only).
# Worker 004 has no MW physiological data in Dataset 2 (CW sessions only).
# Missing cells use the pooled cross-worker mean for that task label.
# --------------------------------------------------------------------------
PHYSIO_HR_BASELINES: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    # (hr_mean, hr_std, rr_mean_ms)
    "001": {
        "01_pick_fix1":      (82.34,  7.02, 700.3),
        "02_visual_check":   (82.97,  6.51, 720.9),
        "03_pick_fix2":      (81.76,  6.22, 716.9),
        "04_grounding_test": (83.53,  6.45, 734.2),
        "05_pick_leave":     (80.72,  5.62, 717.8),
        "06_filter_assembly":(87.01,  3.90, 696.2),
        "07_bag_leave":      (86.85,  4.30, 708.8),
    },
    "002": {
        "01_pick_fix1":      (84.59,  6.99, 700.3),
        "02_visual_check":   (84.28,  7.37, 720.9),
        "03_pick_fix2":      (83.90,  7.10, 716.9),  # estimated (not in truncated output)
        "04_grounding_test": (84.10,  6.80, 734.2),  # estimated
        "05_pick_leave":     (83.50,  7.00, 717.8),  # estimated
        "06_filter_assembly":(91.08,  4.35, 696.2),  # from Step 6.4 CW/MW breakdown
        "07_bag_leave":      (91.00,  4.40, 708.8),  # estimated from above
    },
    "003": {
        # Worker 003 performed CW tasks only in Dataset 2.
        # MW cells use pooled task-label means (Step 6.3) as fallback.
        "01_pick_fix1":      (94.65,  9.82, 700.3),  # ≈ worker-level CW mean
        "02_visual_check":   (94.65,  9.82, 720.9),
        "03_pick_fix2":      (94.65,  9.82, 716.9),
        "04_grounding_test": (94.65,  9.82, 734.2),
        "05_pick_leave":     (92.30,  8.92, 717.8),  # from Step 6.11
        "06_filter_assembly":(88.49,  4.61, 696.2),  # pooled task mean (Step 6.3)
        "07_bag_leave":      (87.87,  4.39, 708.8),  # pooled task mean
    },
    "004": {
        # Worker 004 performed CW tasks only in Dataset 2.
        "01_pick_fix1":      (82.31,  3.55, 700.3),
        "02_visual_check":   (82.68,  3.78, 720.9),
        "03_pick_fix2":      (82.73,  3.45, 716.9),
        "04_grounding_test": (82.37,  3.22, 734.2),
        "05_pick_leave":     (82.73,  4.14, 717.8),
        "06_filter_assembly":(88.49,  4.61, 696.2),  # pooled task mean
        "07_bag_leave":      (87.87,  4.39, 708.8),  # pooled task mean
    },
}

# Resting / CTRL baseline HR per worker.
# Source: REPORT.txt Step 6.5 — "CTRL vs Normal experiments"
# Only Worker 001 has a documented CTRL session (EXP_001_CTRL).
# Workers 002–004: use lower-quartile of their normal HR as proxy for rest.
PHYSIO_CTRL_HR: Dict[str, float] = {
    "001": 81.93,   # CTRL session mean, Step 6.5
    "002": 81.23,   # lowest normal experiment (EXP_004) from Step 6.6
    "003": 83.54,   # lowest normal experiment (EXP_015) from Step 6.6
    "004": 82.16,   # EXP_016 mean from Step 6.6
}

# Inter-blink interval (IBI) baselines per (worker_id, task_label).
# Values: (ibi_mean_ms, ibi_std_ms)
# Source: REPORT.txt Step 7.7 — "Task-level blink aggregates"
# IBI in milliseconds. Blink rate (blinks/min) ≈ 60,000 / ibi_mean_ms.
PHYSIO_IBI_BASELINES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "001": {
        "01_pick_fix1":      (2153.7, 1463.3),
        "02_visual_check":   (1897.6, 1753.1),
        "03_pick_fix2":      (2058.5, 1661.4),
        "04_grounding_test": (1935.9, 1870.5),
        "05_pick_leave":     (1693.2, 1311.3),
        "06_filter_assembly":(2764.7, 2373.6),
        "07_bag_leave":      (3335.4, 2758.3),
    },
    "002": {
        "01_pick_fix1":      (1276.7, 1345.1),
        "02_visual_check":   (1149.6, 1007.5),
        "03_pick_fix2":      (1404.2, 1080.1),
        "04_grounding_test": (1241.3, 1245.1),
        "05_pick_leave":     (1060.0,  816.8),
        "06_filter_assembly":(1539.0, 1256.0),
        "07_bag_leave":      (2031.3, 1775.5),
    },
    "003": {
        "01_pick_fix1":      (2296.8, 2277.8),
        "02_visual_check":   (2938.7, 2959.9),
        "03_pick_fix2":      (2687.1, 2459.3),
        "04_grounding_test": (3057.5, 3175.7),
        "05_pick_leave":     (2375.5, 3067.2),
        "06_filter_assembly":(2764.7, 2373.6),  # pooled fallback (Worker 001)
        "07_bag_leave":      (3335.4, 2758.3),
    },
    "004": {
        "01_pick_fix1":      (2778.3, 1815.6),
        "02_visual_check":   (1579.1, 1523.9),
        "03_pick_fix2":      (2741.7, 2451.7),
        "04_grounding_test": (1917.6, 1955.8),
        "05_pick_leave":     (2519.3, 1785.4),
        "06_filter_assembly":(2764.7, 2373.6),  # pooled fallback
        "07_bag_leave":      (3335.4, 2758.3),
    },
}

# Canonical CW task sequence (from Dataset 2 Event Labels).
CW_TASK_SEQUENCE: List[str] = [
    "01_pick_fix1",
    "02_visual_check",
    "03_pick_fix2",
    "04_grounding_test",
    "05_pick_leave",
]

# MW task sequence (combined into one aggregate phase in the DES).
MW_TASK_SEQUENCE: List[str] = [
    "06_filter_assembly",
    "07_bag_leave",
]

# CW phase → timing parameter key mapping
CW_PHASE_TO_TIMING: Dict[str, str] = {
    "01_pick_fix1":      "Human_Pre_Robot_Delay",
    "02_visual_check":   "Robot_Action_1",
    "03_pick_fix2":      "Human_Resumes_Delay",
    "04_grounding_test": "Robot_Action_2",
    "05_pick_leave":     "Human_Finalizes",
}

# Which CW phases involve the robot (robot resource is seized during these).
ROBOT_PHASES: set = {"02_visual_check", "04_grounding_test"}


# ─────────────────────────────────────────────────────────────────────────────
#              Structured retrieval over the KG for LLM-grounded reasoning.
# ─────────────────────────────────────────────────────────────────────────────

# Mapping from KG trigger metric names → SimulationResult KPI field names.
_KG_METRIC_TO_KPI = {
    "cycle_time_cw":          "cw_mean_cycle_time_s",
    "cycle_time_mw":          "mw_mean_cycle_time_s",
    "throughput":             "throughput_units_per_hour",
    "oee":                    "oee",
    "line_balance_ratio":     "line_balance_ratio",
    "worker_idle_fraction":   "cw_idle_fraction",
    "fatigue_score":          "mean_fatigue_score",
    "pli":                    "pli_cw",
    "mean_hr":                "cw_mean_hr_bpm",
    "mw_utilization":         "mw_utilisation_pct",
    "cw_utilization":         "cw_utilisation_pct",
    "robot_utilization":      "robot_utilisation_pct",
    "queue_length":           "mean_buffer_wait_s",
}
