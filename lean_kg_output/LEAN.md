# MAGI Lean Knowledge Graph — Documentation

## 1. Overview

The MAGI Lean Knowledge Graph (KG) is a structured domain ontology that encodes 26 Lean manufacturing methodologies, their relationships to production problems, KPIs, waste types, and Industry 5.0 principles. It serves as the **retrieval-augmented generation (RAG) knowledge base** for the MAGI Cognitive Agent (Layer 4), grounding LLM reasoning in established Lean methodology rather than relying on parametric knowledge alone.

The KG is stored as two JSON files in `./lean_kg_output/`:
- **`nodes.json`** — 128 nodes across 10 types
- **`edges.json`** — 575 typed, weighted relationships across 19 relation types

## 2. Knowledge Graph Visualizations

### 2.1 Full KG Overview

![Full KG Overview](./magi_outputs/lean_kg_full_overview.png)

The radial layout places **26 Lean methods** (blue, inner ring) at the center, surrounded by 102 peripheral nodes representing problems, KPIs, concepts, waste types, and more. The dense edge network (575 edges, drawn at low opacity) illustrates the rich interconnectedness of Lean methodology.

### 2.2 Core Relationships: Methods → Problems → KPIs

![Core Graph](./magi_outputs/lean_kg_core_graph.png)

This three-column graph shows the primary decision-making pathway used by the Cognitive Agent:
1. **Lean Methods** (left, blue) — the 26 intervention tools available
2. **Problem Types** (center, red) — the 17 detectable manufacturing problems
3. **KPIs** (right, green) — the 19 measurable performance indicators

Edge colors indicate relationship types: `ADDRESSES` (red), `IMPROVES` (green), `TRIGGERS` (orange), `MONITORS` (blue).

### 2.3 Statistics Dashboard

![Statistics](./magi_outputs/lean_kg_statistics.png)

Four panels showing:
- **Node type distribution**: Lean methods (26) and method phases (20) are the most numerous
- **Edge relation distribution**: ADDRESSES (81) and IMPROVES (67) dominate, reflecting the action-oriented design
- **Method categories**: Problem-solving (23%) and improvement (15%) are the largest categories
- **Trigger conditions**: Heijunka has 6 triggers (most reactive), while PDCA and Six Sigma have 1 each (most general)

### 2.4 Method → Problem Heatmap

![Heatmap](./magi_outputs/lean_kg_heatmap.png)

The heatmap shows which Lean methods `ADDRESSES` which problem types, with cell values indicating edge weight (relevance score, 1–5). Key observations:
- **Operator Fatigue** is primarily addressed by Fatigue Analysis (Muri) and Kaizen
- **Production Bottleneck** is addressed by Heijunka, VSM, and Time & Motion Study
- **Quality Defect** has the most methods available (Root Cause Analysis, FMEA, Jidoka, Poka-Yoke, Six Sigma)
- **Line Imbalance** is primarily addressed by Heijunka, Kanban, and Waste Elimination

---

## 3. Node Types

The KG contains **128 nodes** across **10 types**:

| Type | Count | Description |
|------|-------|-------------|
| `lean_method` | 26 | Actionable Lean manufacturing methodologies |
| `method_phase` | 20 | Implementation steps within methods |
| `kpi` | 19 | Measurable performance indicators |
| `problem_type` | 17 | Detectable manufacturing problems |
| `production_concept` | 12 | Abstract Lean/JIT concepts |
| `waste_type` | 11 | Muda (waste) categories |
| `simulation_parameter` | 7 | Digital Twin tunable parameters |
| `physio_signal` | 7 | Physiological sensor channels |
| `lean_pillar` | 5 | Foundational Lean principles |
| `industry5_principle` | 4 | Industry 5.0 values |

### 3.1 Lean Methods (26)

Each method node contains structured metadata enabling automated reasoning:

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (e.g., `heijunka`) |
| `label` | Full name (e.g., "Heijunka (Production Levelling)") |
| `aka` | Alternative names / aliases |
| `description` | Multi-sentence methodology description |
| `lean_category` | Classification (analysis, improvement, problem_solving, etc.) |
| `trigger_conditions` | Array of KPI-threshold rules that activate this method |
| `simulation_adjustments` | Array of Digital Twin parameters this method modifies |
| `expected_kpi_impacts` | Predicted effects on KPIs (direction + magnitude) |
| `references` | Academic references (e.g., "Ohno (1988)", "Liker (2004)") |

**Complete method list by category**:

| Category | Methods |
|----------|---------|
| **Analysis** | Time & Motion Study, Fatigue Analysis (Muri), Learning Curve Optimization, Value Stream Mapping (VSM) |
| **Problem Solving** | Root-Cause Analysis, 5 Whys, FMEA, A3 Problem Solving, DMAIC Cycle, Six Sigma |
| **Improvement** | Kaizen, Waste (Muda) Elimination, Continuous & Autonomous Improvement, Kaikaku |
| **Flow Management** | Kanban, Heijunka (Production Levelling) |
| **Foundational** | Lean Production System, 5S, PDCA Cycle, Standard Work |
| **Error Proofing** | Poka-Yoke, Jidoka (Autonomation) |
| **Monitoring** | SQDCM Dashboard, Andon |
| **Maintenance** | Total Productive Maintenance (TPM) |
| **Strategic** | Hoshin Kanri |

### 3.2 Problem Types (17)

| Problem | Description | Key Trigger |
|---------|-------------|-------------|
| Production Bottleneck | Station throughput mismatch | CW utilisation > 90% |
| Operator Fatigue | Excessive physiological load | fatigue_score > 0.6 |
| Excessive Cycle Time | Task duration exceeding targets | cycle_time > takt × 1.1 |
| Low Throughput | Below-target output rate | throughput < target |
| Quality Defect | Product non-conformance | defect_rate > threshold |
| Unplanned Downtime | Unexpected equipment stops | MTBF < threshold |
| Line Imbalance | CW-MW workload asymmetry | line_balance_ratio < 0.75 |
| Excessive Waiting | Buffer queue delays | queue_wait > 5s |
| Overproduction | Output exceeding demand | WIP > buffer_capacity |
| Excess Inventory | WIP buildup | buffer > 80% capacity |
| Unnecessary Motion | Non-value-adding movement | motion_waste > threshold |
| High Physiological Load | Sustained elevated HR/PLI | PLI > threshold |
| Learning Inefficiency | Slow skill acquisition | cycle_time CV > 0.3 |
| Process Variability | Inconsistent task durations | CV > target |
| Resource Underutilisation | Low equipment/worker usage | utilisation < 50% |
| Safety Risk | Ergonomic or fatigue hazard | fatigue > 0.8 |
| Knowledge Loss | Skill gap or training need | new_worker flag |

### 3.3 KPIs (19)

| KPI | Mapped Simulation Metric |
|-----|--------------------------|
| Throughput | `throughput_units_per_hour` |
| CW Cycle Time | `cw_mean_cycle_time_s` |
| MW Cycle Time | `mw_mean_cycle_time_s` |
| OEE | `oee` |
| Physiological Load Index | `pli_cw`, `pli_mw` |
| Mean Heart Rate | `cw_mean_hr_bpm`, `mw_mean_hr_bpm` |
| CW Station Utilisation | `cw_utilisation_pct` |
| MW Station Utilisation | `mw_utilisation_pct` |
| Robot Utilisation | `robot_utilisation_pct` |
| CW→MW Queue Length | `mean_buffer_wait_s` |
| Line Balance Ratio | `line_balance_ratio` |
| Takt Time Adherence | `takt_adherence` |
| Worker Idle Fraction | `cw_idle_fraction` |
| Total Lead Time | Derived from task log |
| Defect Rate | Quality proxy (assumed ~0 in simulation) |
| Mean Time Between Failures | MTBF (modelled as constant) |
| Mean Time to Repair | MTTR (modelled as constant) |
| First Pass Yield | Quality metric |
| Cumulative Fatigue Score | `mean_fatigue_score`, `peak_fatigue_score` |

---

## 4. Edge Relations (19 Types, 575 Total)

| Relation | Count | Source → Target | Semantics |
|----------|-------|-----------------|-----------|
| `ADDRESSES` | 81 | method → problem | Method resolves this problem type |
| `IMPROVES` | 67 | method → kpi | Method improves this KPI |
| `TRIGGERS` | 47 | problem → method | Problem condition activates this method |
| `EMBODIES` | 42 | method → pillar | Method embodies a Lean pillar |
| `ADJUSTS` | 34 | method → sim_param | Method adjusts this simulation parameter |
| `MONITORS` | 33 | method → kpi | Method requires monitoring this KPI |
| `ALIGNS_WITH` | 32 | method → i5_principle | Method aligns with Industry 5.0 value |
| `ELIMINATES` | 28 | method → waste_type | Method eliminates this type of Muda |
| `MEASURED_BY` | 26 | problem → kpi | Problem is measurable via this KPI |
| `USES` | 25 | method → concept | Method uses this Lean concept |
| `INFLUENCES` | 25 | physio → kpi | Physiological signal influences this KPI |
| `DETECTS` | 24 | kpi → problem | KPI deviation detects this problem |
| `IS_PART_OF` | 24 | concept → pillar | Concept belongs to this Lean pillar |
| `PRECEDES` | 21 | method → method | Method A should precede Method B |
| `HAS_PHASE` | 20 | method → phase | Method has this implementation step |
| `COMPLEMENTS` | 16 | method → method | Methods work well together |
| `REQUIRES` | 12 | method → concept | Method requires this prerequisite |
| `SIGNALS` | 12 | physio → problem | Physiological signal indicates problem |
| `ESCALATES_TO` | 6 | method → method | When Method A fails, escalate to B |

**Each edge carries**:
- `weight` (1–5): Relevance/strength score
- `relation`: Type of relationship
- Additional metadata per relation type (e.g., KPI direction, magnitude for `IMPROVES`)

---

## 5. Trigger Condition System

The trigger condition system is the core mechanism that enables **structured RAG** — matching live KPI values against the KG's encoded rules to find applicable Lean methods.

### 5.1 Trigger Condition Format

Each lean method node contains an array of `trigger_conditions`:

```json
{
  "metric": "line_balance_ratio",
  "operator": "<",
  "threshold": 0.75,
  "priority": 5,
  "threshold_type": "absolute"
}
```

| Field | Values | Description |
|-------|--------|-------------|
| `metric` | KG metric name | Which KPI to check |
| `operator` | `<`, `>`, `>=`, `<=` | Comparison operator |
| `threshold` | numeric | Threshold value |
| `priority` | 1–5 | How critical this trigger is (5 = highest) |
| `threshold_type` | `absolute`, `pct_of_baseline` | Whether to compare against fixed value or baseline % |

### 5.2 Matching Algorithm

The `LeanKGRetriever.retrieve_by_kpi_state()` method:

1. For each lean method, iterate over its trigger conditions
2. Map the KG metric name to the actual simulation KPI value
3. Apply the operator against the threshold
4. If condition fires, accumulate the trigger's priority as a score
5. Rank methods by total accumulated priority score
6. Return top-N methods with context (which conditions fired, why)

This is **deterministic and auditable** — unlike embedding-based RAG, every retrieval decision can be traced to specific KPI thresholds.

### 5.3 Example: Heijunka Activation

Heijunka has 6 trigger conditions. Given baseline KPIs:
- `line_balance_ratio = 0.60` → triggers `< 0.75` (priority 5) ✓
- `throughput = 41.75` → may trigger if below target
- `queue_length = 0.18s` → does not trigger `> 3`

Heijunka scores ≥5, making it a top recommendation for the current line imbalance.

---

## 6. Integration with MAGI Cognitive Agent

### 6.1 RAG Pipeline

```
Live KPIs from DES → LeanKGRetriever → Ranked methods → LLM prompt context
```

The agent uses two tools to interact with the KG:

| Tool | Purpose |
|------|---------|
| `retrieve_lean_methods` | Find methods whose trigger conditions match current KPIs |
| `get_lean_method_detail` | Get full node context (description, phases, adjustments, impacts) |

### 6.2 Agent Decision Flow

```
1. Monitor: Agent reads KPIs via get_current_kpis
2. Diagnose: Agent calls retrieve_lean_methods → KG returns ranked methods
3. Research: Agent calls get_lean_method_detail on top candidate
4. Plan: Agent reads simulation_adjustments and expected_kpi_impacts
5. Act: Agent calls set_takt_time / set_robot_speed / assign_workers
6. Verify: Agent waits for next cycle, re-reads KPIs
```

### 6.3 Knowledge Grounding

The KG ensures the agent's interventions are:
- **Methodologically sound**: Every action maps to a named Lean method
- **Academically referenced**: Each method carries literature references
- **Traceable**: The agent trace log records which KG methods were retrieved and why
- **Bounded**: Trigger conditions prevent irrelevant method suggestions

---

## 7. Academic Foundation

The Lean methods in this KG are grounded in established manufacturing literature:

| Reference | Methods Derived |
|-----------|----------------|
| Ohno, T. (1988). *Toyota Production System* | Kanban, Heijunka, Muda, Jidoka |
| Liker, J. (2004). *The Toyota Way* | 14 TPS principles, PDCA, Standard Work |
| Womack & Jones (2003). *Lean Thinking* | Value Stream Mapping, Pull Systems |
| Rother & Shook (2003). *Learning to See* | VSM methodology |
| Imai, M. (1986). *Kaizen* | Continuous improvement philosophy |
| Deming, W.E. (1986). *Out of the Crisis* | PDCA Cycle, SPC foundations |
| Stamatis, D.H. (2003). *Failure Mode and Effect Analysis* | FMEA methodology |
| Hirano, H. (1995). *5 Pillars of the Visual Workplace* | 5S system |
| Shingo, S. (1986). *Zero Quality Control* | Poka-Yoke |
| EU Commission (2021). *Industry 5.0* | Human-centricity, Sustainability, Resilience |
