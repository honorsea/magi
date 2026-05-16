# Digital Twin Model — Silverline Assembly Line

## 1. Introduction

This document describes the digital twin model of the semi-automated kitchen hood assembly line operated by Silverline Endustri ve Ticaret A.S. at their factory in Amasya, Turkey. The digital twin constitutes the third layer of the MAGI (Manufacturing Agentive Generative Intelligence) framework and provides a virtual replica of the physical production line through Discrete Event Simulation (DES).

The primary purpose of the model is to faithfully replicate the behavior of the physical production line so that the effects of various scenarios on production efficiency and operator ergonomics can be evaluated without disrupting the real system. The model is calibrated using statistical distributions derived from real factory data and physiological baseline profiles extracted from concurrent operator measurements.

### 1.1 Scope

The digital twin model covers the following elements:

- Product arrival modelling based on takt time
- Operational simulation of two sequential workstations (Collaborative Workstation and Manual Workstation)
- Five-phase modelling of the Human-Robot Collaboration (HRC) cycle
- Synthetic generation of operator physiological signals (heart rate, inter-blink interval)
- Within-shift fatigue accumulation modelling
- Computation of production, ergonomic, and Lean manufacturing KPIs

### 1.2 Purpose

The model is designed for a controlled two-scenario comparison:

1. **Baseline Scenario (Mode A):** The production line operating with default parameters and no AI intervention.
2. **MAGI Scenario (Mode B):** The production line monitored, analysed, and optimised in real time by a Cognitive AI Agent.

The statistical comparison between these two scenarios is intended to quantify the impact of AI-driven production optimisation on both operational efficiency and human well-being.

---

## 2. System Description

### 2.1 Overview of the Physical System

The modelled production line consists of two workstations arranged in series along a conveyor system. Products (kitchen hood units) travel from an upstream conveyor, through the Collaborative Workstation, into an inter-station buffer, and finally through the Manual Workstation to the output.

```
  Conveyor --> [Collaborative Workstation (CW)] --> Buffer --> [Manual Workstation (MW)] --> Output
                      (Human + Robot)                               (Human Only)
```

Four volunteer operators staff the line. Each operator is qualified to work at either workstation, and operator assignments are a configurable simulation parameter.

### 2.2 Collaborative Workstation (CW)

The Collaborative Workstation is the station where a human operator and an industrial robot arm work in coordination. Several operations previously performed entirely by hand have been delegated to the robot at this station. Each product passes through five sequential phases:

| Phase | Label | Actor | Description |
|-------|-------|-------|-------------|
| 1 | 01_pick_fix1 | Human | Pick the product from the conveyor and secure it in Fixture 1 |
| 2 | 02_visual_check | Robot | Visual quality control, defect detection, and barcode scan |
| 3 | 03_pick_fix2 | Human | React to robot completion, place barcode label, move product to Fixture 2 |
| 4 | 04_grounding_test | Robot | Electrical grounding verification test |
| 5 | 05_pick_leave | Human | Pack and attach cable, return product to conveyor |

These five phases are executed sequentially for each product. During robot phases (Phase 2 and Phase 4), the robot arm resource is seized and cannot serve any other purpose. The robot arm is a single shared resource; both robot phases are executed by the same arm in sequence within one product cycle.

### 2.3 Manual Workstation (MW)

The Manual Workstation is the second station, operated entirely by a human. Products leaving the Collaborative Workstation pass through the inter-station buffer before reaching this station. The work here consists of two sub-phases:

| Phase | Label | Actor | Description |
|-------|-------|-------|-------------|
| 6 | 06_filter_assembly | Human | Filter assembly, metallic label assembly, and external cleaning |
| 7 | 07_bag_leave | Human | Bagging the product and final barcode verification |

In the simulation, these two sub-phases are modelled as a single aggregate cycle duration sampled from a fitted distribution. The total duration is then split according to an empirical ratio (71.4% filter assembly, 28.6% bagging) derived from the number of ECG records per task label in Dataset 2.

### 2.4 Inter-Station Buffer

A finite-capacity buffer sits between the two workstations, representing the physical holding space on the factory floor. The default buffer capacity is 5 units and is a configurable parameter ranging from 1 to 20 units.

When the buffer is full and a product completes the CW cycle, that product is dropped and counted as lost. This mechanism models real-world conveyor overflow or rework scenarios.

### 2.5 Product Arrival Process

Products arrive at the head of the line at intervals governed by the takt time. In Lean manufacturing, takt time represents the target cycle time derived from customer demand. The default takt time is 60 seconds, and it can be adjusted between 20 and 300 seconds.

Arrivals are not purely deterministic: a small normally distributed jitter is applied to model natural conveyor pacing variability. The coefficient of variation (CV) of this jitter is 0.05 by default.

### 2.6 Operator Pool

Four operators are defined in the system (001, 002, 003, 004), each with a distinct physiological profile. Any operator can be assigned to either workstation. In the default configuration, Operator 001 is assigned to both stations.

The key differences between operator profiles are as follows:

| Operator | Resting Heart Rate (BPM) | Notes |
|----------|--------------------------|-------|
| 001 | 81.93 | Control session data available; low resting HR |
| 002 | 81.23 | Lowest resting heart rate; CW and MW data available |
| 003 | 83.54 | Highest resting heart rate; CW data only |
| 004 | 82.16 | CW data only; low HR variability |

---

## 3. Conceptual Model

### 3.1 Modelling Approach

The digital twin is built on the Discrete Event Simulation (DES) paradigm. In DES, the system state changes only at specific instants in time called events. This approach is well-suited to production lines because state changes — a product arriving at a station, a task completing, a robot phase beginning — are inherently instantaneous events.

The SimPy library serves as the simulation engine. SimPy provides a process-based DES environment and natively supports the modelling constructs needed here: resources (the robot arm), stores (the buffer zones), and concurrent processes (station operations).

### 3.2 Entities

The primary entity in the system is the **product** (kitchen hood unit). Each product is assigned a unique integer identifier and tracked from arrival at the head of the line until it exits the Manual Workstation.

### 3.3 Resources

Three types of resources are defined in the model:

| Resource | Type | Capacity | Description |
|----------|------|----------|-------------|
| CW Input Buffer | Store | Configurable (default: 5) | Queue where products wait to enter the Collaborative Workstation |
| Robot Arm | Resource | 1 | Shared robot; can only execute one phase at a time |
| MW Input Buffer | Store | Configurable (default: 5) | Queue where products wait to enter the Manual Workstation |

### 3.4 Processes

Three concurrent SimPy processes model the operation of the production line:

1. **Arrival Process:** Generates new products at takt-time intervals and inserts them into the CW input buffer.
2. **CW Process:** Pulls products from the buffer, executes the five-phase HRC cycle, and forwards completed products to the MW buffer.
3. **MW Process:** Pulls products from the MW buffer, completes the two-phase manual cycle, and routes the product to the output.

These processes run independently but synchronise through the shared buffer stores. If a buffer is empty, the downstream process waits; if a buffer is full, the incoming product is dropped.

### 3.5 State Variables

The key state variables tracked throughout the simulation are:

- Counts of products generated, dropped, and fully completed
- Total busy time accumulated at each workstation
- Total busy time accumulated by the robot arm
- Start time, end time, and duration for every phase of every product
- Cumulative elapsed working time per operator (used in fatigue modelling)
- Instantaneous physiological signal values per task phase

### 3.6 System Flow

The journey of a product through the line can be summarised as follows:

```
Arrival (governed by takt time)
    |
    v
Wait in CW Input Buffer (if buffer is full --> product is dropped)
    |
    v
Phase 1: Human picks product and secures it in Fixture 1  [Gamma distribution]
    |
    v
Phase 2: Robot performs visual inspection                 [Constant: 35 s / speed factor]
    |
    v
Phase 3: Human repositions product to Fixture 2           [Exponential distribution]
    |
    v
Phase 4: Robot performs grounding test                    [Constant: 30 s / speed factor]
    |
    v
Phase 5: Human packs cable and returns product            [Log-normal distribution]
    |
    v
Wait in MW Input Buffer
    |
    v
Phases 6-7: Human performs filter assembly and bagging    [Normal distribution]
    |
    v
Completed product --> Output
```

At the completion of every phase, a task record (TaskRecord) and a physiological observation record (PhysioRecord) are produced and appended to the simulation log.

---

## 4. Input Data and Statistical Distributions

### 4.1 Data Sources

The digital twin model is calibrated using empirical data from two open-access datasets collected at the same factory, with the same four operators, under the same experimental setup:

| Dataset | Content | Source |
|---------|---------|--------|
| Worker Operation Durations | Video-annotated task durations for four operators across both workstations | Lago Alvarez et al., Open Research Europe, 2025 |
| Worker Physiological Signals | ECG and eye-tracking recordings (heart rate, R-R interval, blinks, fixations, saccades) | Toichoa Eyam, Zenodo, 2025 |

Both datasets were collected under the AI-PRISM project (EU Horizon Europe, Grant No. 101058589).

### 4.2 Task Duration Distributions

The probability distributions used for task durations were selected by the preprocessing pipeline using a bootstrapped Kolmogorov-Smirnov (K-S) goodness-of-fit test with IQR-based outlier filtering applied beforehand. Data from all four operators was pooled before fitting, yielding one representative distribution per phase.

#### Collaborative Workstation (CW) Phase Durations

| Phase | Distribution | Parameters | Approx. Mean | Physical Rationale |
|-------|-------------|------------|--------------|-------------------|
| 01_pick_fix1 | Gamma | shape=13.13, scale=0.52 | ~6.9 s | Motor-skill pickup task; Gamma captures right-skewed physical effort |
| 02_visual_check | Constant | mean=35.0 s | 35.0 s | Deterministic robot action (CV = 0) |
| 03_pick_fix2 | Exponential | scale=2.53 | ~2.5 s | Human reaction time after robot completion; memoryless process |
| 04_grounding_test | Constant | mean=30.0 s | 30.0 s | Deterministic robot action (CV = 0) |
| 05_pick_leave | Log-normal | shape=0.34, scale=10.63 | ~11.3 s | Cable packing task; right-skewed due to occasional slowdowns |

Robot phases (02 and 04) have a coefficient of variation of zero, confirming the deterministic nature of robotic operations. Human phase distributions reflect the stochastic character of manual labour: Gamma for a motor skill placement task, exponential for a reaction-time mechanism, and log-normal for a right-skewed manual task with occasional delays.

#### Manual Workstation (MW) Total Duration

| Phase | Distribution | Parameters | Approx. Mean |
|-------|-------------|------------|--------------|
| Manual Task (06 + 07 combined) | Normal | mean=52.73 s, std=19.19 s | 52.7 s |

The two MW sub-phases are sampled as a single total duration from the Normal distribution and then split proportionally.

### 4.3 Physiological Baseline Values

Per-operator, per-task empirical heart rate (BPM) and inter-blink interval (ms) baselines were extracted from the physiological EDA pipeline. These values form the foundation for synthetic physiological signal generation during simulation.

The model uses a 28-cell baseline table covering four operators and seven task labels. For Operators 003 and 004, Manual Workstation cells are absent from Dataset 2; these are filled with pooled cross-worker means as fallback values.

### 4.4 Modelling Assumptions

The principal assumptions underlying the model are:

1. Data from all four operators is pooled to produce a single CW and a single MW duration distribution. Inter-operator differences in task speed are absorbed into the variability of the fitted distributions rather than modelled as separate operator-level distributions.
2. Robot phases are fully deterministic and exhibit no task-to-task variability.
3. Product arrivals are modelled as takt-time intervals with small Normal jitter. Large-scale conveyor stoppages or scheduled breaks are outside scope.
4. Operator fatigue manifests as a cumulative elevation in physiological signals over the shift but does not directly alter task duration.
5. Product quality defect rates are not modelled explicitly; the OEE quality component is approximated using the ratio of dropped (buffer-overflow) units to total generated units.
6. All task phases are executed without interruption. Unexpected machine stoppages, tool changeovers, or rest breaks are not represented.

---

## 5. Physiological Modelling

### 5.1 Purpose of the Physiological Layer

The digital twin is not solely an operational simulation — it is a human-centric system that monitors operator well-being throughout the simulated shift. This approach is aligned with the central principle of the Industry 5.0 paradigm. The physiological model generates synthetic but realistic physiological observations for every task phase executed by every operator.

### 5.2 Three-Component Heart Rate Model

The instantaneous heart rate (HR) at any point in the simulation is composed of three additive components:

**HR_final = HR_baseline + HR_workload_delta + HR_fatigue_overlay + noise**

**Component 1 — Empirical Baseline:** Derived from the per-(operator, task) mean heart rate and standard deviation measured in Dataset 2. Within-task HR variability is modelled by adding Normal noise scaled to 30% of the operator's empirical standard deviation for that task.

**Component 2 — Workload Delta:** Reflects the physiological response to changes in configurable parameters. When the robot speed factor is increased, the human operator's rest windows between phases shorten, causing sustained heart rate elevation. When takt time is reduced, the metabolic demand on the Manual Workstation operator increases. Coefficients are calibrated against the CW-to-MW heart rate differential observed in the dataset (approximately +4.4 BPM for Operator 001 and +7.2 BPM for Operator 002).

**Component 3 — Fatigue Overlay:** A square-root growth function modelling the gradual drift of heart rate across the shift. The overlay saturates at a physiologically plausible ceiling of 8 BPM above the empirical baseline. This model follows Astrand and Rodahl's (1986) framework for cardiovascular response to sustained moderate-intensity work.

### 5.3 Inter-Blink Interval (IBI) Fatigue Model

The inter-blink interval (IBI) is an indicator of cognitive and visual fatigue. As fatigue accumulates, blink frequency decreases (IBI lengthens). The model represents this effect through a linear growth function:

**IBI_final = IBI_baseline + K_fatigue x elapsed_minutes + noise**

This model is grounded in Galley and Andres' (2002) work on IBI as a fatigue indicator in sustained visual tasks.

### 5.4 Fatigue Score

The model computes a normalised fatigue score in the range [0, 1] for every physiological observation. The score is defined as the ratio of the current HR fatigue overlay to its physiological ceiling.

Fatigue is classified into four actionable levels:

| Level | Score Range | Recommended Action |
|-------|-------------|-------------------|
| Normal | [0.0 -- 0.4) | No action required |
| Elevated | [0.4 -- 0.6) | Continue monitoring |
| Warning | [0.6 -- 0.8) | Consider intervention (increase takt time or swap operator) |
| Critical | [0.8 -- 1.0] | Immediate intervention required |

---

## 6. Configurable Parameters

All tunable parameters of the digital twin are encapsulated in a single configuration object. These parameters can be safely modified at any point, including while the simulation is running.

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| CW Operator ID | 001 | 001--004 | Operator assigned to the Collaborative Workstation |
| MW Operator ID | 001 | 001--004 | Operator assigned to the Manual Workstation |
| Robot Speed Factor | 1.0 | [0.5 -- 2.0] | Multiplier applied to robot phase durations (1.2 = 20% faster) |
| Takt Time | 60 s | [20 -- 300] s | Product inter-arrival interval |
| Buffer Capacity | 5 units | [1 -- 20] | CW-to-MW inter-station buffer size |
| Arrival Jitter CV | 0.05 | >= 0 | Coefficient of variation of Normal noise around takt time |

These parameters are the control variables of the production line. Increasing the robot speed factor shortens the CW cycle time while compressing the operator's recovery windows. Reducing takt time raises production pressure and increases the physiological load on the MW operator. Adjusting buffer capacity directly affects inter-station material flow and WIP inventory levels.

---

## 7. Key Performance Indicators (KPIs)

At the end of each simulation run, the model computes performance indicators across three categories.

### 7.1 Operational KPIs

| KPI | Unit | Description |
|-----|------|-------------|
| Throughput | units/hr | Number of completed products per hour |
| Total Units Produced | units | Total products fully completed during the simulation |
| CW Mean Cycle Time | seconds | Average of the five-phase total at the Collaborative Workstation |
| MW Mean Cycle Time | seconds | Average total duration at the Manual Workstation |
| CW Utilisation Rate | % | Fraction of simulation time the CW operator is busy |
| MW Utilisation Rate | % | Fraction of simulation time the MW operator is busy |
| Robot Utilisation Rate | % | Fraction of simulation time the robot arm is active |
| Mean Buffer Wait Time | seconds | Average time products spend waiting in the inter-station buffer |

### 7.2 Physiological and Ergonomic KPIs

| KPI | Unit | Description |
|-----|------|-------------|
| CW Mean Heart Rate | BPM | Mean heart rate of the CW operator across the shift |
| MW Mean Heart Rate | BPM | Mean heart rate of the MW operator across the shift |
| CW Peak Heart Rate | BPM | Maximum heart rate recorded for the CW operator |
| MW Peak Heart Rate | BPM | Maximum heart rate recorded for the MW operator |
| Physiological Load Index (PLI) -- CW | BPM*min | Cumulative HR elevation above resting baseline, weighted by phase duration |
| Physiological Load Index (PLI) -- MW | BPM*min | Same metric for the MW operator |
| Mean Fatigue Score | [0--1] | Average of all fatigue scores across the shift |
| Peak Fatigue Score | [0--1] | Highest fatigue score recorded during the simulation |

The Physiological Load Index (PLI) is a well-established metric in occupational ergonomics, defined following Kilbom (1990). For each physiological record, the excess HR above the operator's resting (control session) baseline is multiplied by the phase duration in minutes, and these values are summed across the shift.

### 7.3 Lean Manufacturing KPIs

| KPI | Unit | Description |
|-----|------|-------------|
| OEE (Overall Equipment Effectiveness) | [0--1] | Proxy: Availability x Performance x Quality |
| Line Balance Ratio | [0--1] | min(CW cycle time, MW cycle time) / max(CW cycle time, MW cycle time) |
| Takt Adherence | [0--1] | Takt time / bottleneck cycle time (capped at 1.0) |
| CW Idle Fraction | [0--1] | Fraction of CW time spent in robot-wait phases (non-value-adding) |

---

## 8. Operating Modes

### 8.1 Accelerated Mode

The simulation runs as fast as the computer allows. This mode is intended for batch statistical experiments and replication studies. An eight-hour shift completes in seconds, making it practical to run the 30 independent replications required for statistically valid comparisons.

### 8.2 Real-Time Mode

The simulation is paced against wall-clock time using a configurable speed factor. At a factor of 1.0 the simulation runs at true real-time (one simulated second per real second). At a factor of 120.0, one simulated hour passes in 30 real seconds. This mode is designed so that the Cognitive AI Agent can intervene during the simulation, just as a human engineer would on a live production floor.

### 8.3 Statistical Replication

For statistically valid results, the independent replications method is used. Thirty replications are run as standard, each with a different random seed to ensure independence while maintaining reproducibility. Means and 95% confidence intervals are computed across replications, and paired t-tests are used to compare the Baseline and MAGI scenarios.

---

## 9. Validation and Verification

### 9.1 Data-Driven Calibration

All stochastic parameters in the model are derived from real factory data using formal statistical methods. Distribution selection was performed via bootstrapped K-S testing, and outlier filtering was applied before fitting. The deterministic character of robot phases (CV = 0) was confirmed empirically from the raw data.

### 9.2 Physiological Bounds Enforcement

Synthetic physiological signals are clipped to physiologically plausible ranges (HR: 40--200 BPM; IBI >= 100 ms) to prevent non-physical values from propagating into the KPI layer.

### 9.3 Reproducibility

All simulation runs use seeded random number generators. Runs executed with the same seed produce identical results, ensuring full reproducibility of any reported experiment.

---

## 10. Conclusion

This digital twin model provides a comprehensive virtual environment that simultaneously simulates the operational performance and the human factors of the Silverline assembly line. Calibrated with empirically fitted stochastic process durations, physiological signal generation grounded in real operator measurements, and a multi-dimensional KPI computation pipeline, the model constitutes a high-fidelity representation of the physical system.

Through its configurable parameters, the model supports what-if analysis over key decision variables including robot speed, takt time, buffer capacity, and operator assignment. This capability makes the digital twin suitable both as an engineering design tool for scenario evaluation and as the live environment within which an autonomous AI agent can apply and verify Lean manufacturing interventions.
