# MAGI Framework — Technical Documentation

## 1. Overview

**MAGI** (Manufacturing Agentive Generative Intelligence) is a four-layer smart manufacturing framework that integrates Discrete Event Simulation (DES), real-time physiological monitoring, Lean methodology knowledge, and LLM-based cognitive reasoning to optimise a semi-automated assembly line digital twin.

The entire framework is implemented in a single Python file: `magi.py` (3,396 lines, 17 sections).

### 1.1 Origin & Datasets

MAGI is built upon two open-access datasets collected at the **Silverline Endustri Ve Ticaret A.S.** factory in Amasya, Turkey, under the EU Horizon Europe **AI-PRISM** project (Grant No. 101058589):

| Dataset | Source | DOI |
|---------|--------|-----|
| Worker Operation Durations | Lago Alvarez et al., Open Research Europe, 2025 | `10.12688/openreseurope.20530.1` |
| Worker Physiological Signals | Toichoa Eyam, Zenodo, 2025 | `10.5281/zenodo.17658957` |

Four volunteer workers performed tasks across two workstations, with video-annotated task durations and concurrent ECG + eye-tracking physiological recordings.

### 1.2 Four-Layer Architecture

```
┌─────────────────────────────────────────────────┐
│  Layer 4 — Cognitive (LLM Agent + RAG + Tools)  │  Sections 12–16
├─────────────────────────────────────────────────┤
│  Layer 3 — Digital Twin (SimPy DES + KPIs)      │  Sections 6–10
├─────────────────────────────────────────────────┤
│  Layer 2 — Edge (Fatigue Score Computation)     │  Section 5 (fatigue_score)
├─────────────────────────────────────────────────┤
│  Layer 1 — Physical (Physiological Simulator)   │  Sections 1–5
└─────────────────────────────────────────────────┘
```

**Layer 1 (Physical)** generates synthetic physiological signals (HR, IBI, fatigue) using empirical baselines from Dataset 2. **Layer 2 (Edge)** computes a normalised fatigue score. **Layer 3 (Digital Twin)** runs the full DES with operational and physiological KPIs. **Layer 4 (Cognitive)** is an LLM-based AI agent that monitors, reasons, and acts on the digital twin autonomously.

### 1.3 Assembly Line Layout

The Silverline assembly line consists of two consecutive workstations:

```
  Conveyor → [CW: Collaborative Workstation] → Buffer → [MW: Manual Workstation] → Output
                  (Human + Robot)                            (Human only)
```

**Collaborative Workstation (CW)** — 5 phases per product cycle:

| Phase | Label | Actor | Description |
|-------|-------|-------|-------------|
| 1 | `01_pick_fix1` | Human | Pick product from conveyor, fix in Fixture 1 |
| 2 | `02_visual_check` | Robot | Visual inspection, defect detection, barcode scan |
| 3 | `03_pick_fix2` | Human | React to robot completion, place barcode, move to Fixture 2 |
| 4 | `04_grounding_test` | Robot | Electrical grounding verification |
| 5 | `05_pick_leave` | Human | Pack cable, attach, return product to conveyor |

**Manual Workstation (MW)** — 2 phases modelled as 1 aggregate:

| Phase | Label | Actor | Description |
|-------|-------|-------|-------------|
| 6 | `06_filter_assembly` | Human | Filter assembly, metallic label, external cleaning |
| 7 | `07_bag_leave` | Human | Bagging, final barcode verification |

### 1.4 Experimental Design

The framework runs a controlled experiment:

1. **Phase 1 — Baseline**: Accelerated DES with default parameters, no AI intervention
2. **Phase 2 — MAGI**: Real-time DES with the Cognitive Agent actively monitoring and optimising
3. **Phase 3 — Statistical Comparison**: 30 paired replications comparing baseline vs. MAGI's final configuration
4. **Phase 4 — Report**: Output files, KPI comparison table, paired t-tests

### 1.5 Hypothesis

> The MAGI Cognitive Agent, guided by Lean manufacturing knowledge and real-time physiological monitoring, can autonomously improve production KPIs (throughput, OEE, line balance) while simultaneously reducing operator fatigue indicators (PLI, mean HR, fatigue score) compared to an unoptimised baseline configuration.

---

## 2. Environment & Dependencies

### 2.1 Python Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| `simpy` | ≥ 4.0 | Discrete Event Simulation engine |
| `numpy` | ≥ 1.22 | Numerical computation |
| `scipy` | ≥ 1.9 | Statistical distributions (gamma, lognorm, expon, norm) |
| `pandas` | ≥ 2.0 | DataFrame operations, CSV export |
| `google-genai` | ≥ 1.0 | Google Gemini / Gemma LLM API |
| `python-dotenv` | any | `.env` file loading |
| `ortools` | ≥ 9.0 | Operations Research models (agent code execution) |
| `matplotlib` | any | Visualisations (agent code execution) |

### 2.2 Configuration

**API Key**: Set in `.env` file at the project root:
```
GOOGLE_API_KEY=your_key_here
```

**Command-line arguments**:

| Argument | Default | Description |
|----------|---------|-------------|
| `--speed` | `120.0` | Simulation speed factor for MAGI run |
| `--duration` | `8.0` | Simulated shift duration (hours) |
| `--replications` | `30` | Statistical replications for comparison |
| `--seed` | `1000` | Base random seed |
| `--model` | `gemma-4-31b` | LLM model name |
| `--skip-magi` | `False` | Skip the MAGI run (baseline only) |
| `--output-dir` | `./magi_outputs` | Output directory |

### 2.3 Input Files

| File | Location | Content |
|------|----------|---------|
| `lean_kg_output/nodes.json` | Project root | 26 Lean method nodes + 17 problem types + KPI/concept nodes |
| `lean_kg_output/edges.json` | Project root | 575 typed relationships (ADDRESSES, IMPROVES, MONITORS, etc.) |
| `.env` | Project root | API key |

### 2.4 Output Files

All outputs are saved to `./magi_outputs/`:

| File | Content |
|------|---------|
| `baseline_task_log.csv` | Full event log from baseline run (TaskRecord rows) |
| `magi_task_log.csv` | Full event log from MAGI run |
| `agent_trace.json` | Complete agent reasoning trace (every cycle, tool call, response) |
| `magi_final_config.json` | Configuration after agent optimisation |
| `replications_baseline.csv` | KPIs from 30 baseline replications |
| `replications_magi.csv` | KPIs from 30 MAGI-config replications |
| `kpi_comparison.csv` | Paired t-test results |
| `scratch/*.py` | Agent-generated Python scripts |
| `*.png` | Agent-generated visualisations |

---

## 3. Section-by-Section Reference

### 3.0 Section 0 — Imports & Module-Level Constants (Lines 57–107)

Standard library and third-party imports. Notable conditional imports:

- `google.genai` / `google.genai.types` — loaded in a `try/except` block; sets `HAS_GENAI = True/False`
- `dotenv.load_dotenv()` — loads `.env` file if `python-dotenv` is installed
- `sys.stdout.reconfigure(encoding="utf-8")` — forces UTF-8 output on Windows consoles

### 3.1 Section 1 — Empirical Distribution Parameters (Lines 109–226)

**Purpose**: Stores the statistically fitted probability distributions derived from `1_data_preprocessing.py`.

**Provenance**: Each distribution was selected via bootstrapped Kolmogorov-Smirnov (K-S) goodness-of-fit testing with IQR outlier filtering applied to pooled data from all 4 workers.

#### `CW_TIMING_PARAMS` — Collaborative Workstation Phase Durations

| Phase | Distribution | Parameters | Physical Meaning |
|-------|-------------|------------|------------------|
| `Human_Pre_Robot_Delay` | `gamma(a=13.13, loc=0, scale=0.52)` | Shape=13.13, Scale=0.52 | Time for human to pick and fixture product (~6.9s mean) |
| `Robot_Action_1` | `constant(35.0)` | Mean=35.0, CV=0.000 | Deterministic robot visual inspection |
| `Human_Resumes_Delay` | `expon(loc=0, scale=2.53)` | Scale=2.53 | Human reaction time after robot completes (~2.5s mean) |
| `Robot_Action_2` | `constant(30.0)` | Mean=30.0, CV=0.000 | Deterministic robot grounding test |
| `Human_Finalizes` | `lognorm(s=0.34, loc=0, scale=10.63)` | Shape=0.34, Scale=10.63 | Cable packing + return (~11.3s mean, right-skewed) |

#### `MW_TIMING_PARAMS` — Manual Workstation Duration

| Phase | Distribution | Parameters | Physical Meaning |
|-------|-------------|------------|------------------|
| `Manual_Task_Duration` | `norm(mean=52.73, std=19.19)` | Mean=52.73s, Std=19.19s | Combined filter assembly + bagging |

#### `load_timing_params_from_json(path)`

Utility function to override distribution parameters from a JSON file at runtime.

### 3.2 Section 2 — Empirical Physiological Baseline Tables (Lines 228–364)

**Purpose**: Stores per-worker, per-task physiological baselines extracted from `2_physiological_eda.py`.

#### `PHYSIO_HR_BASELINES` — Heart Rate Profiles

Structure: `Dict[worker_id → Dict[task_label → (hr_mean, hr_std, rr_mean_ms)]]`

- 4 workers × 7 task labels = 28 cells
- Workers 003 and 004 have no MW data in Dataset 2; their MW cells use pooled cross-worker means as fallback
- Values sourced from REPORT.txt Step 6.11 ("Task-level ECG aggregates")

#### `PHYSIO_CTRL_HR` — Resting Heart Rate Baselines

| Worker | CTRL HR (BPM) | Source |
|--------|--------------|--------|
| 001 | 81.93 | CTRL session (EXP_001_CTRL) |
| 002 | 81.23 | Lowest normal experiment (EXP_004) |
| 003 | 83.54 | Lowest normal experiment (EXP_015) |
| 004 | 82.16 | EXP_016 mean |

These baselines are critical for fatigue detection: HR elevation >12% above CTRL triggers a Muri (overburden) alert.

#### `PHYSIO_IBI_BASELINES` — Inter-Blink Interval Profiles

Structure: `Dict[worker_id → Dict[task_label → (ibi_mean_ms, ibi_std_ms)]]`

- Blink rate ≈ 60,000 / ibi_mean_ms
- IBI elongation indicates cognitive fatigue (Galley & Andrés, 2002)
- Workers 003/004 MW cells use Worker 001 values as pooled fallback

#### Task Sequence Constants

- `CW_TASK_SEQUENCE`: `["01_pick_fix1", "02_visual_check", "03_pick_fix2", "04_grounding_test", "05_pick_leave"]`
- `MW_TASK_SEQUENCE`: `["06_filter_assembly", "07_bag_leave"]`
- `CW_PHASE_TO_TIMING`: Maps each CW task label to its timing parameter key
- `ROBOT_PHASES`: `{"02_visual_check", "04_grounding_test"}` — phases where the robot resource is seized

### 3.3 Section 3 — ConfigState (Lines 366–435)

**Purpose**: Thread-safe, runtime-modifiable configuration for all tunable simulation parameters.

```python
@dataclass
class ConfigState:
    cw_worker_id:           str   = "001"
    mw_worker_id:           str   = "001"
    robot_speed_factor:     float = 1.0
    takt_time_seconds:      float = 60.0
    buffer_capacity:        int   = 5
    simulation_speed_factor:float = 1.0
    inter_arrival_jitter_cv:float = 0.05
```

**Thread safety**: Uses `threading.RLock()` via the `update(**kwargs)` method, allowing the Cognitive Agent (running in a different thread context) to modify parameters mid-simulation without race conditions.

**Key methods**:
- `update(**kwargs)` — Atomically update one or more parameters
- `snapshot() → Dict` — Return a copy of all parameters as a dictionary

**Parameter constraints** (enforced by ToolAPI, not ConfigState):

| Parameter | Range | Effect |
|-----------|-------|--------|
| `robot_speed_factor` | [0.5, 2.0] | Robot phase durations divided by this factor |
| `takt_time_seconds` | [20, 300] | Product arrival interval |
| `buffer_capacity` | [1, 20] | CW→MW WIP buffer size |
| `simulation_speed_factor` | [0.1, 10000] | Wall-clock pacing ratio |


### 3.4 Section 4 — TaskDurationSampler (Lines 437–503)

**Purpose**: Generates stochastic task durations by sampling from the fitted distributions in Section 1.

**Class**: `TaskDurationSampler(config: ConfigState)`

The sampler reads the `robot_speed_factor` from `ConfigState` at call time (not at init), enabling the Cognitive Agent to change robot speed mid-simulation.

**Key methods**:

| Method | Returns | Behaviour |
|--------|---------|-----------|
| `sample_cw_phase(phase_label)` | `float` (seconds) | Samples from the distribution for the given CW phase. Robot phases (`02_visual_check`, `04_grounding_test`) are divided by `config.robot_speed_factor`. |
| `sample_mw_cycle()` | `float` (seconds) | Samples from `norm(52.73, 19.19)` with a floor of 5.0s to prevent degenerate durations. |
| `sample_arrival_interval()` | `float` (seconds) | Returns `takt_time_seconds × (1 + N(0, inter_arrival_jitter_cv))`, floored at 1.0s. |

**Distribution sampling logic**:
```
gamma   → scipy.stats.gamma.rvs(shape, loc, scale)
expon   → scipy.stats.expon.rvs(loc, scale)
lognorm → scipy.stats.lognorm.rvs(shape, loc, scale)
norm    → numpy.random.normal(mean, std_dev)
constant→ mean (deterministic)
```

### 3.5 Section 5 — PhysiologicalSampler (Lines 505–834)

**Purpose**: Generates synthetic physiological signals (heart rate, R-R interval, inter-blink interval, fatigue score) for each task phase, modelling Layer 1 (Physical) and Layer 2 (Edge) of the MAGI stack.

**Class**: `PhysiologicalSampler(config: ConfigState)`

**Data class**: `PhysioRecord` — one record per task phase per worker:

```python
@dataclass
class PhysioRecord:
    sim_time:          float   # Simulation clock (seconds)
    worker_id:         str     # "001"–"004"
    workstation:       str     # "CW" or "MW"
    task_label:        str     # e.g. "01_pick_fix1"
    hr_bpm:            float   # Final heart rate (BPM)
    rr_interval_ms:    float   # R-R interval (ms)
    ibi_ms:            float   # Inter-blink interval (ms)
    hr_baseline:       float   # Empirical baseline HR for this (worker, task)
    hr_delta:          float   # Workload delta (speed/pace driven)
    hr_fatigue:        float   # Fatigue-driven HR drift
    fatigue_score:     float   # Normalised [0, 1] composite fatigue score
    elapsed_minutes:   float   # Cumulative worked time
```

**Three-component HR model**:

```
HR_final = HR_baseline + HR_delta(workload) + HR_fatigue(elapsed_time) + noise
```

1. **HR_baseline**: Looked up from `PHYSIO_HR_BASELINES[worker_id][task_label]`
2. **HR_delta (workload)**: Driven by robot speed factor and takt time pace
   - CW phases: `delta = speed_factor_effect × 2.5 BPM` (higher robot speed → shorter human recovery)
   - MW phases: `delta = takt_pace_effect × 1.5 BPM`
3. **HR_fatigue (temporal drift)**: Åstrand & Rodahl (1986) cardiovascular drift model
   - `drift = K × ln(1 + elapsed_minutes / tau) × workload_intensity`
   - K = 3.5 BPM, tau = 60 min
   - Models gradual HR elevation over an 8-hour shift
4. **Noise**: `N(0, empirical_std × 0.3)` — scaled to 30% of worker's empirical HR variability

**Inter-Blink Interval (IBI) fatigue model** (Galley & Andrés, 2002):

```
IBI_final = IBI_baseline + K_fatigue × elapsed_minutes + noise
```
- `K_fatigue = 2.5 ms/min` — linear IBI elongation (blink rate slows with fatigue)
- Noise: `N(0, empirical_std × 0.25)`

**Fatigue score computation** (Layer 2 — Edge):

```
fatigue_score = clip(0.4 × normalised_HR_elevation + 0.6 × normalised_time_fraction, 0, 1)
```
- HR elevation: `(HR_final - CTRL_HR) / CTRL_HR`, normalised to [0, 1]
- Time fraction: `elapsed_minutes / (shift_hours × 60)`
- Weights: 40% physiological signal, 60% temporal accumulation
- The 60% time weight reflects that fatigue is primarily cumulative (not instantaneous)

**Workload intensity** (combined metric):

```
workload_intensity = min(robot_speed_factor × takt_pace_intensity, 2.0)
```
Where `takt_pace_intensity = 60.0 / takt_time_seconds` (higher pace → higher intensity).

### 3.6 Section 6 — Task & KPI Record Data Classes (Lines 836–939)

**`TaskRecord`** — logged at completion of each task phase:

| Field | Type | Description |
|-------|------|-------------|
| `product_id` | `int` | Sequential product identifier |
| `workstation` | `str` | `"CW"` or `"MW"` |
| `task_label` | `str` | E.g. `"01_pick_fix1"` |
| `worker_id` | `str` | Active worker at this station |
| `phase_start_time` | `float` | SimPy clock at phase start |
| `phase_end_time` | `float` | SimPy clock at phase end |
| `phase_duration` | `float` | `end - start` in seconds |
| `is_robot_phase` | `bool` | Whether robot resource was seized |
| `queue_wait_time` | `float` | Wait time in buffer before this phase |
| `physio` | `PhysioRecord?` | Attached physiological sample |

**`SimulationResult`** — complete output of one `dt.run()` call:

| Field | Type | Description |
|-------|------|-------------|
| `config_snapshot` | `Dict` | Configuration at run start |
| `seed` | `int` | Random seed |
| `duration_hours` | `float` | Simulated duration |
| `task_log` | `List[TaskRecord]` | Full event log |
| `physio_log` | `List[PhysioRecord]` | Full physiological log |
| `kpis` | `Dict[str, Any]` | Computed KPI dictionary |
| `run_timestamp` | `str` | ISO timestamp |

**Methods**:
- `to_dataframe()` → Flattened `pd.DataFrame` for CSV export
- `summary()` → Formatted KPI report string

### 3.7 Section 7 — SimPy Process Definitions (Lines 941–1210)

Three concurrent SimPy generator processes model the assembly line:

#### `_arrival_process(env, buffer, sampler, config, counters)`

- Generates products at takt-time intervals with jitter
- Pushes product IDs into the CW input `simpy.Store`
- If buffer is full → product is dropped (models conveyor overflow)
- `counters["dropped"]` tracks lost units

#### `_cw_process(env, buffer, mw_buffer, robot, config, dur_sampler, phy_sampler, task_log, physio_log, cw_busy_time, robot_busy)`

- Continuously pulls products from CW buffer
- Executes the 5-phase HRC sequence:
  - Phases 2 & 4: Seizes `robot` resource (`simpy.Resource(capacity=1)`)
  - All phases: Samples duration from `TaskDurationSampler`
  - All phases: Emits `PhysioRecord` via `PhysiologicalSampler`
- Completed products are pushed to `mw_buffer` (the inter-station queue)
- Tracks `cw_busy_time` for utilisation calculations

#### `_mw_process(env, mw_buffer, config, dur_sampler, phy_sampler, task_log, physio_log, mw_busy_time, counters)`

- Pulls products from `mw_buffer`
- Executes 2-phase MW cycle as one aggregate duration
- Logs two `TaskRecord` entries (one per MW task label) with proportional duration split (70% filter assembly, 30% bagging)
- Increments `counters["completed"]`

### 3.8 Section 8 — KPI Computation Engine & Digital Twin Class (Lines 1212–1530)

#### `KPIComputer` (static utility class)

Computes all KPIs from raw logs after simulation completion:

**Operational KPIs**:

| KPI | Formula | Unit |
|-----|---------|------|
| `throughput_units_per_hour` | `completed / sim_hours` | units/hr |
| `total_units_produced` | count of MW-completed products | units |
| `cw_mean_cycle_time_s` | mean of per-product CW total time | seconds |
| `mw_mean_cycle_time_s` | mean of per-product MW total time | seconds |
| `cw_utilisation_pct` | `sum(cw_busy) / sim_duration × 100` | % |
| `mw_utilisation_pct` | `sum(mw_busy) / sim_duration × 100` | % |
| `robot_utilisation_pct` | `sum(robot_busy) / sim_duration × 100` | % |
| `mean_buffer_wait_s` | mean queue wait across all CW tasks | seconds |

**Physiological KPIs**:

| KPI | Formula | Unit |
|-----|---------|------|
| `cw_mean_hr_bpm` | mean HR across CW physio records | BPM |
| `mw_mean_hr_bpm` | mean HR across MW physio records | BPM |
| `cw_peak_hr_bpm` | max HR across CW records | BPM |
| `mw_peak_hr_bpm` | max HR across MW records | BPM |
| `pli_cw` | Physiological Load Index = Σ(HR × duration) / 60 | BPM·min |
| `pli_mw` | Same for MW | BPM·min |
| `mean_fatigue_score` | mean of all `fatigue_score` values | [0, 1] |
| `peak_fatigue_score` | max `fatigue_score` | [0, 1] |

**Lean KPIs**:

| KPI | Formula | Unit |
|-----|---------|------|
| `oee` | `availability × performance × quality` (proxy) | [0, 1] |
| `line_balance_ratio` | `min(CW_ct, MW_ct) / max(CW_ct, MW_ct)` | [0, 1] |
| `takt_adherence` | fraction of cycles within ±10% of takt time | [0, 1] |
| `cw_idle_fraction` | fraction of CW time spent in non-value-adding phases | [0, 1] |

#### `DigitalTwin` Class

The main orchestrator. Holds `ConfigState`, creates SimPy environment, and runs simulations.

**Constructor**: `DigitalTwin(config: ConfigState = None)`
- Creates `TaskDurationSampler` and `PhysiologicalSampler`
- Stores a `_last_result` for ToolAPI access

**Key method**: `run(duration_hours, seed, realtime=False, step_callback=None) → SimulationResult`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `duration_hours` | 8.0 | Simulated shift length |
| `seed` | 42 | Random seed for reproducibility |
| `realtime` | `False` | If `True`, paces simulation to wall-clock time using `simulation_speed_factor` |
| `step_callback` | `None` | Function called after every SimPy event (used by Cognitive Agent) |

**Real-time mode**: When `realtime=True`, after each SimPy event:
```python
expected_wall = env.now / speed_factor
actual_wall = time.perf_counter() - wall_t0
sleep_needed = expected_wall - actual_wall
if sleep_needed > 0:
    time.sleep(sleep_needed)
```
This synchronises simulation progress with wall-clock time, allowing the Cognitive Agent to intervene mid-run. The `speed_factor` is re-read from `ConfigState` each iteration, enabling runtime speed changes.

### 3.9 Section 9 — Tool API (Lines 1532–1920)

**Purpose**: Clean interface for the Cognitive Layer to interact with the Digital Twin. All parameter modifications go through this API, which enforces validation and bounds.

**Class**: `ToolAPI(dt: DigitalTwin)`

#### Core Tools (1–8)

| # | Method | Description |
|---|--------|-------------|
| 1 | `get_current_kpis()` | Returns full KPI dict from last completed run |
| 2 | `run_scenario(duration, seed, config_overrides)` | Run a fresh scenario with optional config changes |
| 3 | `set_robot_speed_factor(factor)` | Adjust robot speed [0.5, 2.0] |
| 4 | `assign_workers(cw_id, mw_id)` | Reassign workers to stations |
| 5 | `set_takt_time(takt_seconds)` | Set takt time [20, 300] |
| 6 | `set_buffer_capacity(capacity)` | Set WIP buffer [1, 20] |
| 7 | `get_config_snapshot()` | Read current config as dict |
| 8 | `compare_kpis(baseline, current)` | Compute % delta for key KPIs |

#### Extended Tools (9–11)

| # | Method | Description |
|---|--------|-------------|
| 9 | `get_physio_summary(last_n)` | Aggregated physio stats from last run |
| 10 | `get_live_physio_summary(physio_log)` | Live physio stats during real-time run |
| 11 | `set_simulation_speed(factor)` | Change simulation speed at runtime |

All setter tools return a `Dict` with `{"success": True, "previous": old, "new": new}` or `{"error": "message"}`.

### 3.10 Section 10 — Replication Runner (Lines 1922–2060)

**Purpose**: Runs N independent replications for statistically valid comparison.

**Class**: `ReplicationRunner(dt: DigitalTwin)`

**Key methods**:

| Method | Description |
|--------|-------------|
| `run_replications(n, duration_hours, base_seed, label)` | Run n replications with seeds `base_seed + i`, return DataFrame |
| `compute_paired_comparison(df_a, df_b)` (static) | Paired t-test between two replication DataFrames |

**Paired comparison**: For each KPI, computes:
- Mean difference (MAGI − Baseline)
- Percentage change
- t-statistic and p-value (`scipy.stats.ttest_rel`)
- Significance flag (p < 0.05)

This follows the **independent replications method** (Law, 2015, *Simulation Modeling and Analysis*, 5th ed.).


### 3.11 Section 12 — Lean Knowledge Graph RAG Engine (Lines 2062–2253)

**Purpose**: Provides structured retrieval over the Lean Knowledge Graph (KG) to ground the LLM agent's reasoning in domain-specific methodology.

**Design Decision — Structured RAG, not Embedding-Based**: The KG is small (26 methods, 575 edges). Instead of using an embedding model for semantic similarity search, this component matches the KG's own encoded `trigger_conditions` against live KPI values. This is more academically rigorous because it uses the KG's domain logic directly.

#### KG Structure

**Nodes** (from `nodes.json`):

| Node Type | Count | Examples |
|-----------|-------|---------|
| `lean_method` | 26 | Kaizen, Muri Analysis, Heijunka, VSM, 5S, Kanban, PDCA, etc. |
| `problem_type` | 17 | Bottleneck, Operator Fatigue, Quality Defect, Line Imbalance, etc. |
| `kpi` | ~15 | throughput, oee, cycle_time_cw, pli, fatigue_score, etc. |
| `concept` | ~10 | JIT, Pull System, Takt Time Concept, One-Piece Flow, etc. |
| `lean_pillar` | 4 | Kaizen Pillar, Jidoka Pillar, Heijunka Pillar, Respect for People |
| `industry5_value` | 4 | Human-Centricity, Sustainability, Resilience, Technology Synergy |

**Edges** (from `edges.json`):

| Relation | Count | Meaning |
|----------|-------|---------|
| `ADDRESSES` | ~80 | Method solves a problem type |
| `IMPROVES` | ~60 | Method improves a KPI (with direction + magnitude) |
| `MONITORS` | ~40 | Method requires monitoring a KPI |
| `PRECEDES` | ~20 | Method A should come before Method B |
| `ESCALATES_TO` | ~15 | When Method A fails, escalate to Method B |
| `ADJUSTS` | ~30 | Method adjusts a simulation parameter |
| `EMBODIES` | ~25 | Method embodies a lean pillar |
| `ALIGNS_WITH` | ~20 | Method aligns with an Industry 5.0 value |

**Each lean method node contains**:

```json
{
  "id": "heijunka",
  "type": "lean_method",
  "label": "Heijunka (Production Levelling)",
  "aka": ["Production Levelling", "Level Loading", ...],
  "description": "...",
  "lean_category": "flow_management",
  "trigger_conditions": [
    {"metric": "line_balance_ratio", "operator": "<", "threshold": 0.75, "priority": 5},
    {"metric": "queue_length", "operator": ">", "threshold": 3, "priority": 4},
    ...
  ],
  "simulation_adjustments": [
    {"parameter": "production_pace_factor", "direction": "optimize", ...},
    {"parameter": "worker_assignment", "direction": "reassign", ...}
  ],
  "expected_kpi_impacts": [
    {"kpi": "throughput", "direction": "increase", "magnitude": 4, ...}
  ],
  "references": ["Ohno (1988)", "Liker (2004)"]
}
```

#### `LeanKGRetriever` Class

| Method | Description |
|--------|-------------|
| `retrieve_by_kpi_state(kpis, baseline_kpis, top_n)` | Match trigger conditions against live KPIs; return ranked methods |
| `retrieve_by_method_name(name)` | Fuzzy-match a method by label or alias |
| `retrieve_by_problem_type(problem_id)` | Find methods connected via `ADDRESSES` edges |
| `get_full_context_for_method(method_id)` | Return node + all connected edges + neighbour nodes |
| `get_all_method_names()` | List all method labels |
| `get_method_summary_text()` | One-liner per method for system prompt embedding |

#### KPI-to-Trigger Metric Mapping

The KG uses its own metric names in trigger conditions. These are mapped to actual SimulationResult KPI fields:

| KG Trigger Metric | SimulationResult KPI | Scale Conversion |
|---|---|---|
| `cycle_time_cw` | `cw_mean_cycle_time_s` | None |
| `throughput` | `throughput_units_per_hour` | None |
| `oee` | `oee` | None |
| `line_balance_ratio` | `line_balance_ratio` | None |
| `fatigue_score` | `mean_fatigue_score` | ×100 (KG uses 0–100) |
| `pli` | `pli_cw` | None |
| `mean_hr` | `cw_mean_hr_bpm` | None |
| `mw_utilization` | `mw_utilisation_pct` | ÷100 (KG uses 0–1) |
| `robot_utilization` | `robot_utilisation_pct` | ÷100 |
| `queue_length` | `mean_buffer_wait_s` | None |

For `pct_of_baseline` threshold types, the comparison is against stored baseline KPIs.

### 3.12 Section 13 — Code Execution Sandbox (Lines 2255–2377)

**Purpose**: Allows the Cognitive Agent to generate and execute Python code for mathematical modelling, visualisations, and analysis.

**Class**: `CodeSandbox(output_dir="./magi_outputs")`

#### Security Measures

1. **Import whitelist**: Only allowed imports: `numpy`, `scipy`, `pandas`, `matplotlib`, `ortools`, `json`, `math`, `collections`, `dataclasses`, `statistics`, `itertools`, `functools`, `textwrap`, `datetime`
2. **Blocked patterns** (regex-validated before execution): `import os`, `import sys`, `import subprocess`, `import shutil`, `import socket`, `__import__`, `exec(`, `eval(`, `compile(`, `globals(`, `locals(`
3. **Timeout**: 60 seconds per execution
4. **Isolated subprocess**: Code runs in `subprocess.run()` with `sys.executable`

#### Execution Flow

```
1. Agent generates Python code via LLM
2. CodeSandbox validates against blocked patterns
3. Code is prepended with sandbox header:
   - matplotlib.use('Agg')  # non-interactive backend
   - _OUTPUT_DIR = "<absolute_path>"
4. Written to ./magi_outputs/scratch/agent_code_N.py
5. Executed via subprocess with 60s timeout
6. stdout, stderr, and newly created files returned to agent
```

#### Return Value

```python
{
    "success": bool,
    "stdout": str,         # capped at 5000 chars
    "stderr": str,         # capped at 3000 chars
    "files_created": list, # absolute paths of new files
    "script_path": str,    # path to the saved script
}
```

### 3.13 Section 14 — Fatigue Monitor (Lines 2379–2468)

**Purpose**: Classifies operator fatigue from live physiological signals into actionable levels.

**Class**: `FatigueMonitor`

#### Fatigue Classification Levels

| Level | Score Range | Agent Action |
|-------|------------|-------------|
| **Normal** | [0.0, 0.4) | No action needed |
| **Elevated** | [0.4, 0.6) | Log observation, continue monitoring |
| **Warning** | [0.6, 0.8) | Suggest intervention (slow takt, swap workers) |
| **Critical** | [0.8, 1.0] | Immediate intervention required |

#### Cross-Validation Metrics

For each worker, the monitor reports:

| Metric | Description | Fatigue Indicator |
|--------|-------------|-------------------|
| `mean_fatigue_score` | Average of recent fatigue scores | Primary classifier |
| `max_fatigue_score` | Peak fatigue score in window | Spike detection |
| `hr_elevation_pct` | `(mean_HR - CTRL_HR) / CTRL_HR × 100` | >12% = cardiovascular overload |
| `ibi_elevation_pct` | `(mean_IBI - baseline_IBI) / baseline_IBI × 100` | IBI elongation = cognitive fatigue |

#### `assess(physio_log, config, window_records=30) → Dict`

Returns per-worker fatigue status:
```python
{
    "status": "ok",
    "workers": {
        "CW_001": {
            "worker_id": "001",
            "fatigue_level": "warning",
            "mean_fatigue_score": 0.65,
            "hr_elevation_pct": 14.2,
            "needs_intervention": True,
            ...
        },
        "MW_001": { ... }
    }
}
```

### 3.14 Section 15 — Cognitive Agent (Lines 2470–3020)

**Purpose**: The LLM-based AI agent that autonomously monitors, reasons about, and optimises the digital twin.

This is the core of Layer 4 — the largest and most complex section.

#### System Prompt

The system prompt (`_MAGI_SYSTEM_PROMPT`) instructs the LLM to:

1. **Act as a manufacturing engineer** operating the Silverline digital twin
2. **Follow PDCA** (Plan-Do-Check-Act) for every intervention
3. **Prioritise operator wellbeing** — fatigue ≥ 0.8 requires immediate action
4. **Use the knowledge base** via `retrieve_lean_methods` and `get_lean_method_detail`
5. **Execute code** for OR-Tools optimisation and matplotlib visualisation
6. **Log reasoning** for post-run review
7. **Stay grounded** — only use data from tools, never fabricate metrics

The prompt is parameterised with `{method_list}` — the names of all 26 lean methods in the KG.

#### LLM Tool Registry

11 tools exposed as Gemini `FunctionDeclaration` objects:

| Tool | Description | Maps To |
|------|-------------|---------|
| `get_current_kpis` | Read all KPIs | Live computation from task/physio logs |
| `set_robot_speed_factor` | Adjust robot speed [0.5, 2.0] | `ToolAPI.set_robot_speed_factor()` |
| `assign_workers` | Reassign workers to CW/MW | `ToolAPI.assign_workers()` |
| `set_takt_time` | Change takt time [20, 300]s | `ToolAPI.set_takt_time()` |
| `set_buffer_capacity` | Change WIP buffer [1, 20] | `ToolAPI.set_buffer_capacity()` |
| `get_config_snapshot` | Read current config | `ToolAPI.get_config_snapshot()` |
| `retrieve_lean_methods` | RAG: find applicable lean methods | `LeanKGRetriever.retrieve_by_kpi_state()` |
| `get_lean_method_detail` | RAG: get full method detail | `LeanKGRetriever.retrieve_by_method_name()` |
| `execute_python_code` | Run Python code (OR-Tools, plots) | `CodeSandbox.execute()` |
| `get_fatigue_status` | Get fatigue classification per worker | `FatigueMonitor.assess()` |
| `log_reasoning` | Record reasoning for post-run review | Internal trace log |

#### Agentic Tool-Use Loop

Each monitoring cycle uses a multi-turn tool-calling loop:

```
1. Build state summary (KPIs + fatigue + config + baseline comparison)
2. Inject user messages (if any)
3. Send to LLM
4. LOOP (max 8 rounds):
   a. Receive response
   b. If text only → done
   c. If function calls → execute each, feed results back
   d. Continue loop with updated history
5. Log trace entry
```

**Max rounds**: 8 tool-call rounds per cycle (prevents infinite loops).

#### Conversation History Management

- Maintained as `List[genai_types.Content]` (Gemini API format)
- Truncated to last 30 entries when exceeding 40 (prevents token overflow)
- User messages from the CLI are injected as part of the monitoring cycle message

#### Live KPI Computation

During real-time simulation, KPIs are computed on-the-fly from the live `task_log` and `physio_log` (since the formal `KPIComputer` only runs after simulation completion):

```python
def _compute_live_kpis(task_log, physio_log) → Dict:
    # Count completed products, compute throughput
    # Calculate mean cycle times from per-product phase sums
    # Aggregate physio statistics
    # Compute approximate OEE and line balance ratio
```

#### Agent Trace (`AgentTraceEntry`)

Every monitoring cycle produces a trace entry:

```python
@dataclass
class AgentTraceEntry:
    sim_time_s:    float              # Simulation time
    wall_time:     str                # Wall-clock timestamp
    trigger:       str                # "auto_monitor" | "user_message" | "fatigue_alert"
    state_summary: Dict[str, Any]     # KPIs + fatigue + config at this point
    user_message:  Optional[str]      # User's CLI message (if any)
    agent_text:    str                # LLM's response text
    tool_calls:    List[Dict]         # Tools called (name + args)
    tool_results:  List[Dict]         # Tool results (name + result)
    files_created: List[str]          # Files created by code execution
```

After the simulation, the full trace is:
- Saved to `agent_trace.json`
- Printed as a summary table (`print_trace_summary()`)

### 3.15 Section 16 — Main Entry Point (Lines 3022–3396)

#### `_print_banner(text)` — ASCII banner for phase headers

#### `_run_magi_simulation(dt, api, agent, duration_hours, seed, speed_factor) → SimulationResult`

Orchestrates the real-time MAGI run with interactive CLI:

**Threading model**:
```
Main Thread:    CLI input loop (blocking reads with msvcrt on Windows)
Sim Thread:     dt.run(realtime=True, step_callback=agent_callback)
Communication:  queue.Queue for user → agent messages
```

**Agent callback** (called after every SimPy event):
```python
def agent_callback(env, task_log, physio_log):
    if enough_sim_time_passed OR user_has_messages:
        agent.monitor_cycle(env, task_log, physio_log, user_messages)
```

**Polling interval**: 30 simulated minutes between autonomous monitoring cycles. User messages trigger an immediate cycle.

**CLI commands**:

| Command | Effect |
|---------|--------|
| `status` | Print current config |
| `speed <N>` | Change sim speed to Nx |
| `pause` | Set speed to 0.001x |
| `resume` | Restore original speed |
| `quit` / `exit` | Stop simulation |
| `help` | List commands |
| Any other text | Queue as message to AI agent |

#### `__main__` — Experiment Runner

**Phase 1 — Baseline** (accelerated):
- `DigitalTwin(ConfigState(cw="001", mw="001", robot=1.0, takt=60.0))` 
- `dt.run(duration_hours=8, seed=1000)` — instant execution
- Results saved; KPIs stored as baseline reference

**Phase 2 — MAGI** (real-time with agent):
- Fresh `DigitalTwin` with same baseline config + speed factor
- Initialise `LeanKGRetriever`, `CodeSandbox`, `FatigueMonitor`, `CognitiveAgent`
- Agent receives baseline KPIs for comparison
- `_run_magi_simulation()` — interactive real-time run
- Agent trace, final config, and task log saved

**Phase 3 — Statistical Comparison** (30 replications):
- 30 baseline replications (default config, accelerated)
- 30 MAGI replications (agent's final config, accelerated)
- Paired t-test for each KPI (`scipy.stats.ttest_rel`)

**Phase 4 — Report**:
- Print comparison table
- List all output files
- Print agent activity statistics

---

## 4. Design Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| **Single-file architecture** | Academic reproducibility — one file, one execution, complete traceability |
| **SimPy for DES** | Industry-standard Python DES library; generator-based process semantics match assembly line flow |
| **Empirical distributions** | All timing parameters fitted to real Silverline data; no synthetic assumptions |
| **Three-component HR model** | Combines task-specific baselines (empirical), workload dynamics (mechanistic), and fatigue drift (literature: Åstrand & Rodahl 1986) |
| **IBI fatigue indicator** | Blink rate slowing is an established cognitive fatigue marker (Galley & Andrés, 2002) |
| **Structured RAG over KG** | Trigger-condition matching is deterministic and auditable; more rigorous than embedding similarity for a small domain |
| **Paired replications** | Standard method for simulation comparison (Law, 2015); 30 replications provides statistical power |
| **Thread-safe ConfigState** | Allows the Cognitive Agent (separate thread context) to modify parameters mid-simulation |
| **Code sandbox** | Enables OR-Tools and matplotlib without exposing the host system to arbitrary code execution |
| **Full agent trace** | Every reasoning step, tool call, and result is logged for academic auditability |

---

## 5. Key Algorithms & Models

### 5.1 Fatigue Score (Layer 2)
```
fatigue_score = clip(0.4 × HR_elevation_norm + 0.6 × time_fraction, 0, 1)
```

### 5.2 HR Cardiovascular Drift (Åstrand & Rodahl, 1986)
```
HR_fatigue = K × ln(1 + elapsed_min / tau) × workload_intensity
K = 3.5 BPM, tau = 60 min
```

### 5.3 IBI Fatigue Drift (Galley & Andrés, 2002)
```
IBI_drift = 2.5 × elapsed_minutes (ms)
```

### 5.4 Physiological Load Index (Kilbom, 1990)
```
PLI = Σ(HR_i × duration_i) / 60  (BPM·min)
```

### 5.5 OEE Proxy
```
OEE = availability × performance × quality
availability = (sim_duration - unplanned_downtime) / sim_duration
performance = actual_throughput / (sim_duration / takt_time)
quality = 1 - defect_rate  (≈ 1.0 in simulation)
```

### 5.6 Line Balance Ratio
```
LBR = min(mean_CW_cycle_time, mean_MW_cycle_time) / max(mean_CW_cycle_time, mean_MW_cycle_time)
```
Ideal = 1.0 (perfectly balanced). The baseline shows LBR ≈ 0.60, indicating significant CW–MW imbalance.
