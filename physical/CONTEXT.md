# AI-PRISM Siverline Assembly Line Datasets

## 1. Project Background

This project introduces two datasets collected from a semi-automated assembly line featuring two workstations, one manual and one collaborative, where four workers executed standardized tasks in a real factory belonging to Silverline Endustri Ve Ticaret A.S. (Silverline).

The datasets for this project were collected under the AI-PRISM project (*AI-Powered Human-Centred Robot Interactions for Smart Manufacturing*), funded by the European Union's Horizon Europe research and innovation programme under grant agreement No. 101058589.

### Participants

- **Number of workers:** 4 volunteer workers from Silverline
- **Data collection period:** October 2024
- **Sessions:** Multiple sessions per worker
- **Ethical approval:** Granted by the Academic Ethics Committee of the Tampere Region on November 20, 2023 (Statement 165/2023, concerning statement request 51/2023)
- **Ethics framework:** Finnish National Board on Research Integrity (TENK)
- **Consent:** Written informed consent obtained from all participants; GDPR-compliant data handling practices applied
- **Anonymisation:** Participant identifiers were anonymised in the datasets

### Keywords

Human Robot Collaboration, AI, Robotics, Reasoning Acting and Control, collaborative ambient, flexible production, Social Sciences and Humanities, programming by demonstration, Open Access Network

## 2. Factory & Assembly Line Setup

### 2.1 Company Background
- **Company:** Silverline Endustri Ve Ticaret A.S. (Silverline Appliances Co.)
- **Location:** Amasya, Turkey
- **Sector:** Home appliances manufacturer

### 2.2 Physical Layout
The datasets focused specifically on the final testing and labelling stations of a hood assembly line. Although the overall workflow was familiar to operators (having previously been performed fully manually), the presented layout was a new configuration for the workers involved in the study. The assembly line consists of two consecutive workstations:

| Workstation Type | Operated By |
|-|-|
| Collaborative | Robot + Human operator |
| Manual | Human operator |

### 2.3 Collaborative Workstation (Workstation 1)
At the collaborative workstation, some of the operations that were previously done by humans were now handled by the robot. The process at the collaborative station is as follows:

1. Product (hood) is picked from a conveyor and fixed into a dedicated fixture by the operator.
2. Robot executes functional tests to verify product operability:
   - Defect detection in the glass surface
   - Barcode inspection
   - Visual quality control
   - Grounding tests
3. Robot conducts visual inspection and barcode control.
4. Operator places a barcode inside the product.
5. Operator moves the product to a second fixture for grounding tests.
6. Robot performs the grounding tests.
7. Operator packs the cable and attaches it to the product.
7. Operator returns the product to the conveyor.

### 2.4 Manual Workstation (Workstation 2)
A second human operator performs the following final tasks:

- Filter assembly
- Metallic label assembly
- External cleaning
- Bagging
- Final barcode verification/check

## 3. Dataset 1 - Workers Operation Durations in Assembly Tasks

### 3.1 Publication Details
- **Title:** Dataset of workers operation durations in assembly tasks
- **Authors:** Angela Lago Alvarez (Tampere University, FAST-LAb), Gulen Canbul, Oktay Gun, Engin Talas (Silverline), Jose Luis Martinez Lastra (Tampere University, FAST-LAb)
- **Published:** 18 June 2025
- **Journal:** Open Research Europe, 5:164
- **DOI:** https://doi.org/10.12688/openreseurope.20530.1
- **Access:** Open access - Creative Commons Attribution 4.0 International (CC-BY 4.0)
- **Repository:** Zenodo - https://zenodo.org/records/15340717

### 3.2 Data Collection Procedure
- All task execution sessions were video recorded.
- Recordings were subsequently reviewed and manually annotated to extract precise task durations.

### 3.3 Data Cleaning & Preprocessing
The raw data underwent the following steps:
- Removal of incomplete or misaligned records.
- Anonymisation of participant identifiers.
- Outlier filtering using the Interquartile Range (IQR) method.

### 3.4 Dataset Structure
The dataset has over 180 task-level records per worker and comprises 8 separate CSV files, each corresponding to a unique worker-workstation combination:

#### Collaborative Workstation Files: `CW1.csv` - `CW4.csv`
One file per worker (Worker_ID001 to Worker_ID004). Each file logs task execution divided into operations.

| Column | Description |
|--------|-------------|
| Units processed | Cumulative number of completed units |
| Grab | Time when the operator initiates handling of a component |
| R1 start | Start time of the robot's first action |
| R1 stop | End time of the robot's first action |
| Pick | Time when the operator resumes manual work |
| R2 start | Start time of the robot's second action |
| R2 stop | End time of the robot's second action |
| End | Completion time of the assembly operation |

- Time format: `hh:mm:ss`, relative to the start of the session.

#### Manual Workstation Files: `MW1.csv` - `MW4.csv`
One file per worker (Worker_ID001 to Worker_ID004). Documents manually performed assembly tasks.

| Column | Description |
|--------|-------------|
| Units processed | Cumulative number of completed units |
| Start | Task start time for each unit |
| End | Task completion time for each unit |

- Time format: `hh:mm:ss`, relative to the session start.
- Workers had prior experience with the manual workstation tasks, enabling comparative analysis between experienced manual performance and initial collaborative task exposure.

## 4. Dataset 2 - Workers Physiological Signals During Assembly Tasks

### 4.1 Publication Details
- **Title:** Dataset of Workers Physiological Signals During Assembly Tasks
- **Author/Researcher:** Toichoa Eyam, Aitor
- **Published:** November 20, 2025 (Version v1)
- **DOI:** https://doi.org/10.5281/zenodo.17658957
- **Access:** Open - Creative Commons Attribution 4.0 International
- **Repository:** Zenodo

### 4.2 Signal Types Recorded
The dataset includes signals derived from two physiological domains:

| Domain | Instrument Used | Signal Categories |
|-|-|-|
| Cardiovascular | ECG chest band | ECG data |
| Ocular activity | Eye-tracking glasses | Blinks, Fixations, Saccades |

### 4.3 Dataset Structure
The dataset is divided into 4 ZIP files, one per operator (`001.zip`, `002.zip`, `003.zip`, `004.zip`).

Inside each ZIP, there are four folders:
- `blinks/`
- `ecg/`
- `fixations/`
- `saccades/`

Each folder contains multiple `.csv` files corresponding to different recording sessions.

### 4.4 Common CSV Columns (Generic Identifiers)
All CSV files share the following generic identifier columns:

| Column | Description |
|--------|-------------|
| Worker ID | Identifier for the operator |
| Experiment Name | Name/code of the experiment session |
| Event Label | Task the operator was performing; for eye-tracking, may also indicate what the operator was looking at (e.g., task name or colleague) |
| Event Group | Primarily identifies product numbers handled during the session; for eye-tracking, may also indicate whether the operator was looking at a product or another worker |
| Start | Beginning of the event described in Event Label (ECG); or event start (eye-tracking) |
| End | End of the event |

### 4.5 Eye-Tracking Specific Notes
- The `Event Label` column may include the stimulus the operator was looking at (e.g., a specific task or a colleague/worker).
- The `Event Group` column can indicate whether the operator was looking at a product or another worker.

### 5.6 ECG Specific Notes
- `Start` and `End` columns mark the beginning and end of the event described in `Event Label`.
- `Timestamp` specifies when the data was collected.

## 5. Relationship Between the Two Datasets

Both datasets originate from the same experimental setup, same four workers, same factory, and same assembly line. The physiological signals dataset is explicitly listed as **supplemented by** the operation durations dataset, indicating they are designed to be used together for multimodal human performance analysis.

| Attribute | Operation Durations Dataset | Physiological Signals Dataset |
|-|-|-|
| Workers | 4 (ID001-ID004) | 4 (001-004) |
| Workstations | Manual + Collaborative | Manual + Collaborative |
| Data type | Time-stamped task durations | ECG + Eye-tracking signals |
| Format | CSV (8 files) | CSV files inside 4 ZIP archives |

## 6. Real Data Observations (from File Excerpts)

### 6.1 CW1.csv - Collaborative Workstation, Worker 1

**Format details:**
- Delimiter: semicolon (`;`)
- Time format: `h.mm.ss` (dot-separated, single digit for hours, e.g. `0.02.31`, `1.04.32`)
- Total records: **196 units** across multiple recording sessions
- Sessions are concatenated in a single file; timestamps reset to `0.00.xx` at the start of each session (there is no explicit session ID column)

**Example rows:**
```
Units processed;Grab;R1 start;R1 stop;Pick;R2 start;R2 stop;End
1;0.00.10;0.00.29;0.01.04;0.01.18;0.01.40;0.02.11;0.02.31
2;0.02.07;0.02.17;0.02.52;0.02.53;0.03.11;0.03.41;0.04.29
```

**Observed timing ranges (approximate, from session samples):**
- Grab → R1 start (human pre-robot delay): ~5-15 seconds
- R1 start → R1 stop (robot first action): ~35 seconds (consistent, robot-controlled)
- R1 stop → Pick (human resumes): ~5-90 seconds (variable, reflects operator pace)
- R2 start → R2 stop (robot second action): ~30 seconds (consistent)
- Pick → End (human finalises): ~10-80 seconds

**Anomalies and notable patterns:**
- In some sessions (e.g. units 61-113), the R1 stop timestamps appear significantly higher than surrounding values, suggesting a different robot cycle or timing anomaly in that session block.
- Some R2 start and R2 stop values are identical (e.g. unit 61: `R2 start = 0.02.11; R2 stop = 0.02.11`), suggesting the robot's second phase was skipped or instantaneous for those units.
- Units reset to low values (e.g. unit 11 starts at `0.01.10`) indicating a new recording session beginning within the same file.

---

### 6.2 MW1.csv - Manual Workstation, Worker 1

**Format details:**
- Delimiter: semicolon (`;`)
- Time format: `h.mm.ss` (same as CW files)
- Column header uses **"Stop"** (not "End" as described in the paper's documentation)
- Total records: **283 units** across multiple recording sessions
- Six trailing empty columns present in every row (likely a formatting artifact)

**Example rows:**
```
Units processed;Start;Stop;;;;;
1;0.00.04;0.01.10;;;;;
2;0.01.36;0.02.34;;;;;
```

**Observed task duration ranges:**
- Minimum: ~16 seconds (unit 268: `1.11.15` → `1.11.31`)
- Typical range: ~40-90 seconds per unit
- Maximum observed: ~5 minutes (unit 273: `1.11.41` → `1.16.46`, likely an interruption or anomaly)
- Median duration: approximately 60-70 seconds per unit

**Comparison with collaborative workstation:**
- The manual workstation shows more continuous task flow (consecutive units follow directly from each other with small gaps), whereas the collaborative workstation has structured robot-action intervals embedded in each cycle.
- Workers had prior experience at the manual station, which is reflected in generally tighter and more consistent durations compared to the collaborative workstation records.

---

### 6.3 Blinks - `001_blinks_EXP_002.csv`

**Format:** Comma-separated (`,`)

**Columns:**
| Column | Description | Units / Format |
|--------|-------------|---------------|
| Blink Start | Unix timestamp of blink onset | Milliseconds (epoch) |
| Blink End | Unix timestamp of blink offset | Milliseconds (epoch) |
| Blink Duration | Duration of the blink | Milliseconds |
| Interblink Interval | Time since the previous blink ended | Milliseconds |
| Event Label | Assembly task being performed | String (see task codes below) |
| Event Group | Hood/product unit being processed | String (e.g. `H1`, `H2`, ...) |
| Worker ID | Anonymised worker identifier | String (e.g. `001`) |
| Experiment Name | Session identifier | String (e.g. `EXP_002`) |

**Observed blink duration range:** ~100 ms - 764 ms (typical: 300-560 ms)

**Observed interblink interval range:** ~8 ms - ~11,192 ms

**Event Labels observed in this file:**
- `01_pick_fix1` — operator picks product and places it in fixture 1
- `02_visual_check` — robot performs visual/barcode inspection
- `03_pick_fix2` — operator moves product to fixture 2
- `04_grounding_test` — robot performs grounding test
- `05_pick_leave` — operator retrieves product and returns it to conveyor

**Event Groups observed:** `H1` through `H7` (each represents one hood/product unit in the session)

---

### 6.4 ECG - `001_ecg_EXP_009_5.csv`

**Format:** Comma-separated (`,`)

**Columns:**
| Column | Description | Units / Format |
|--------|-------------|---------------|
| Start | Unix timestamp marking start of the labelled event | Milliseconds (epoch) |
| End | Unix timestamp marking end of the labelled event | Milliseconds (epoch) |
| Timestamp | Unix timestamp of the individual ECG measurement | Milliseconds (epoch) |
| Heart rate | Instantaneous heart rate | BPM |
| R-R interval | Time between consecutive R-peaks | Milliseconds |
| Event Label | Assembly task at time of measurement | String |
| Event Group | Hood/product unit identifier | String (e.g. `H1`, `H2`, ...) |
| Worker ID | Worker identifier | String |
| Experiment Name | Session identifier | String |

**Sampling:** Approximately 1 measurement per second per event; multiple R-R intervals recorded per second when consecutive heartbeats fall within the same second window.

**Observed heart rate range:** 72-85 BPM (within this session file)

**Observed R-R interval range:** ~640-916 ms

**Event Labels observed:** `01_pick_fix1`, `02_visual_check`, `03_pick_fix2`, `04_grounding_test`, `05_pick_leave`

**Event Groups observed:** `H1` through `H6` (in this session file)

**Note on Start/End columns:** Unlike the eye-tracking files, the ECG `Start` and `End` columns refer to the **boundaries of the entire event segment** (i.e., the whole duration of a task like `04_grounding_test`), not the individual measurement. The `Timestamp` column gives the precise moment of each heartbeat reading within that segment.

---

### 6.5 Fixations - `001_fixations_EXP_012_4.csv`

**Format:** Comma-separated (`,`)

**Columns:**
| Column | Description | Units / Format |
|--------|-------------|---------------|
| Fixation Start | Unix timestamp of fixation onset | Milliseconds (epoch) |
| Fixation End | Unix timestamp of fixation offset | Milliseconds (epoch) |
| Fixation Duration | Duration of the fixation | Milliseconds |
| Fixation Dispersion | Spatial spread of the fixation | Degrees (visual angle) |
| Event Label | Assembly task or gaze target | String |
| Event Group | Product unit or gaze category | String |
| Worker ID | Worker identifier | String |
| Experiment Name | Session identifier | String |

**Observed fixation duration range:** ~20 ms - 316 ms (typical: 60-175 ms)

**Observed fixation dispersion range:** ~0.05° - 1.18°

**Event Labels observed:**
- `06_filter_assembly` — operator assembles filter at the manual workstation
- `07_bag_leave` — operator bags the product and finalises
- `Worker` — operator is looking at a colleague (gaze target is another person)

**Event Group special value:** When `Event Label = Worker`, the `Event Group` is also set to `Worker`, indicating the operator's gaze was directed at another person rather than a product.

**Note:** This file covers the **manual workstation** tasks (filter assembly and bagging), contrasting with the ECG and blinks files which cover the **collaborative workstation** tasks.

---

### 6.6 Saccades - `001_saccades_EXP_001_CTRL.csv`

**Format:** Comma-separated (`,`)

**Columns:**
| Column | Description | Units / Format |
|--------|-------------|---------------|
| Saccade Start | Unix timestamp of saccade onset | Milliseconds (epoch) |
| Saccade End | Unix timestamp of saccade offset | Milliseconds (epoch) |
| Saccade Duration | Duration of the eye movement | Milliseconds |
| Saccade Amplitude | Angular size of the saccade | Degrees |
| Saccade Peak Velocity | Maximum angular velocity | Degrees/second |
| Saccade Peak Acceleration | Maximum angular acceleration | Degrees/second² |
| Saccade Peak Deceleration | Maximum angular deceleration (negative) | Degrees/second² |
| Event Label | Assembly task being performed | String |
| Event Group | Hood/product unit identifier | String |
| Worker ID | Worker identifier | String |
| Experiment Name | Session identifier | String |

**Scale:** This is the largest file — over **15,600 saccade records** in a single control session (`EXP_001_CTRL`), spanning product units `H1` through `H11`.

**Observed saccade duration range:** ~4 ms - 392 ms

**Observed saccade amplitude range:** ~0.1° - 50.4° (small micro-saccades to large scanning movements)

**Observed peak velocity range:** ~49 - 2,289 degrees/second

**Peak acceleration / deceleration:** Values can reach ~482,000 deg/s² (acceleration) and ~-481,600 deg/s² (deceleration) for the largest saccades.

**Note — data quality:** Some rows have missing values for `Saccade Peak Deceleration` (blank field), occurring mainly for very short-duration saccades (≤10 ms).

**Note — label typo:** In this file, the grounding test label appears as `04_groudning_test` (with "groudning" misspelled) rather than the correct `04_grounding_test` used in all other files. This is a known inconsistency in the raw data.

**Event Labels observed:** `01_pick_fix1`, `02_visual_check`, `03_pick_fix2`, `04_groudning_test` *(typo in source)*, and implicitly other task phases across the session.

---

### 6.7 Unified Event Label Reference

All physiological signal files share a common set of event labels corresponding to named steps in the assembly workflow. Based on the observed data:

| Event Label | Workstation | Description |
|-------------|------------|-------------|
| `01_pick_fix1` | Collaborative | Operator picks hood from conveyor and fixes it in Fixture 1 |
| `02_visual_check` | Collaborative | Robot performs visual inspection and barcode control |
| `03_pick_fix2` | Collaborative | Operator moves product from Fixture 1 to Fixture 2; barcode placement |
| `04_grounding_test` | Collaborative | Robot performs grounding test; cable packing by operator |
| `05_pick_leave` | Collaborative | Operator retrieves product and returns it to conveyor |
| `06_filter_assembly` | Manual | Operator performs filter and metallic label assembly, external cleaning |
| `07_bag_leave` | Manual | Operator bags the product and performs final barcode check |
| `Worker` | Either | Gaze target is a colleague (eye-tracking only; used as both Event Label and Event Group) |

---

### 6.8 Timestamp Format Notes

- All physiological signal files use **Unix epoch timestamps in milliseconds** (13-digit integers), not the `h.mm.ss` format used in the operation duration CSVs.
- The operation duration files (CW/MW) use session-relative times starting from `0.00.xx` at the beginning of each recording session.
- To align physiological signals with operational timing, the session start Unix timestamp would need to be known and used as an offset.

---

## Dataset Directory Structure

C:.
│ 
│
├───Dataset of workers operation durations in assembly tasks
│       CW1.csv
│       CW2.csv
│       CW3.csv
│       CW4.csv
│       MW1.csv
│       MW2.csv
│       MW3.csv
│       MW4.csv
│
└───Dataset of Workers Physiological Signals During Assembly Tasks
    │
    ├───001
    │   ├───blinks
    │   │       001_blinks_EXP_001_CTRL.csv
    │   │       001_blinks_EXP_002.csv
    │   │       001_blinks_EXP_003.csv
    │   │       001_blinks_EXP_009.1.csv
    │   │       001_blinks_EXP_009.2.csv
    │   │       001_blinks_EXP_009.3.csv
    │   │       001_blinks_EXP_009.4.csv
    │   │       001_blinks_EXP_009.5.csv
    │   │       001_blinks_EXP_009.csv
    │   │       001_blinks_EXP_012.2.csv
    │   │       001_blinks_EXP_012.3.csv
    │   │       001_blinks_EXP_012.4.csv
    │   │       001_blinks_EXP_012.5.csv
    │   │       001_blinks_EXP_012.6.csv
    │   │       001_blinks_EXP_012.7.csv
    │   │       001_blinks_EXP_012.8.csv
    │   │       001_blinks_EXP_012.csv
    │   │
    │   ├───ecg
    │   │       001_ecg_EXP_001_CTRL.csv
    │   │       001_ecg_EXP_002.csv
    │   │       001_ecg_EXP_003.csv
    │   │       001_ecg_EXP_009.1.csv
    │   │       001_ecg_EXP_009.2.csv
    │   │       001_ecg_EXP_009.3.csv
    │   │       001_ecg_EXP_009.4.csv
    │   │       001_ecg_EXP_009.5.csv
    │   │       001_ecg_EXP_009.csv
    │   │       001_ecg_EXP_012.2.csv
    │   │       001_ecg_EXP_012.3.csv
    │   │       001_ecg_EXP_012.4.csv
    │   │       001_ecg_EXP_012.5.csv
    │   │       001_ecg_EXP_012.6.csv
    │   │       001_ecg_EXP_012.7.csv
    │   │       001_ecg_EXP_012.8.csv
    │   │       001_ecg_EXP_012.csv
    │   │
    │   ├───fixations
    │   │       001_fixations_EXP_001_CTRL.csv
    │   │       001_fixations_EXP_002.csv
    │   │       001_fixations_EXP_003.csv
    │   │       001_fixations_EXP_009.1.csv
    │   │       001_fixations_EXP_009.2.csv
    │   │       001_fixations_EXP_009.3.csv
    │   │       001_fixations_EXP_009.4.csv
    │   │       001_fixations_EXP_009.5.csv
    │   │       001_fixations_EXP_009.csv
    │   │       001_fixations_EXP_012.2.csv
    │   │       001_fixations_EXP_012.3.csv
    │   │       001_fixations_EXP_012.4.csv
    │   │       001_fixations_EXP_012.5.csv
    │   │       001_fixations_EXP_012.6.csv
    │   │       001_fixations_EXP_012.7.csv
    │   │       001_fixations_EXP_012.8.csv
    │   │       001_fixations_EXP_012.csv
    │   │
    │   └───saccades
    │           001_saccades_EXP_001_CTRL.csv
    │           001_saccades_EXP_002.csv
    │           001_saccades_EXP_003.csv
    │           001_saccades_EXP_009.1.csv
    │           001_saccades_EXP_009.2.csv
    │           001_saccades_EXP_009.3.csv
    │           001_saccades_EXP_009.4.csv
    │           001_saccades_EXP_009.5.csv
    │           001_saccades_EXP_009.csv
    │           001_saccades_EXP_012.2.csv
    │           001_saccades_EXP_012.3.csv
    │           001_saccades_EXP_012.4.csv
    │           001_saccades_EXP_012.5.csv
    │           001_saccades_EXP_012.6.csv
    │           001_saccades_EXP_012.7.csv
    │           001_saccades_EXP_012.8.csv
    │           001_saccades_EXP_012.csv
    │
    ├───002
    │   ├───blinks
    │   │       002_blinks_EXP_004.csv
    │   │       002_blinks_EXP_006.1.csv
    │   │       002_blinks_EXP_006.2.csv
    │   │       002_blinks_EXP_006.csv
    │   │       002_blinks_EXP_007.2.csv
    │   │       002_blinks_EXP_007.4.csv
    │   │       002_blinks_EXP_007.csv
    │   │       002_blinks_EXP_008.2.csv
    │   │       002_blinks_EXP_008.3.csv
    │   │       002_blinks_EXP_008.4.csv
    │   │       002_blinks_EXP_008.5.csv
    │   │       002_blinks_EXP_008.csv
    │   │       002_blinks_EXP_010.2.csv
    │   │       002_blinks_EXP_010.3.csv
    │   │       002_blinks_EXP_010.4.csv
    │   │       002_blinks_EXP_010.5.csv
    │   │       002_blinks_EXP_010.6.csv
    │   │       002_blinks_EXP_010.csv
    │   │       002_blinks_EXP_011.2.csv
    │   │       002_blinks_EXP_011.3.csv
    │   │       002_blinks_EXP_011.4.csv
    │   │       002_blinks_EXP_011.6.csv
    │   │       002_blinks_EXP_011.csv
    │   │
    │   ├───ecg
    │   │       002_ecg_EXP_004.csv
    │   │       002_ecg_EXP_006.1.csv
    │   │       002_ecg_EXP_006.2.csv
    │   │       002_ecg_EXP_006.csv
    │   │       002_ecg_EXP_007.2.csv
    │   │       002_ecg_EXP_007.4.csv
    │   │       002_ecg_EXP_007.csv
    │   │       002_ecg_EXP_008.2.csv
    │   │       002_ecg_EXP_008.3.csv
    │   │       002_ecg_EXP_008.4.csv
    │   │       002_ecg_EXP_008.5.csv
    │   │       002_ecg_EXP_008.csv
    │   │       002_ecg_EXP_010.2.csv
    │   │       002_ecg_EXP_010.3.csv
    │   │       002_ecg_EXP_010.4.csv
    │   │       002_ecg_EXP_010.5.csv
    │   │       002_ecg_EXP_010.6.csv
    │   │       002_ecg_EXP_010.csv
    │   │       002_ecg_EXP_011.2.csv
    │   │       002_ecg_EXP_011.3.csv
    │   │       002_ecg_EXP_011.4.csv
    │   │       002_ecg_EXP_011.6.csv
    │   │       002_ecg_EXP_011.csv
    │   │
    │   ├───fixations
    │   │       002_fixations_EXP_004.csv
    │   │       002_fixations_EXP_006.1.csv
    │   │       002_fixations_EXP_006.2.csv
    │   │       002_fixations_EXP_006.csv
    │   │       002_fixations_EXP_007.2.csv
    │   │       002_fixations_EXP_007.4.csv
    │   │       002_fixations_EXP_007.csv
    │   │       002_fixations_EXP_008.2.csv
    │   │       002_fixations_EXP_008.3.csv
    │   │       002_fixations_EXP_008.4.csv
    │   │       002_fixations_EXP_008.5.csv
    │   │       002_fixations_EXP_008.csv
    │   │       002_fixations_EXP_010.2.csv
    │   │       002_fixations_EXP_010.3.csv
    │   │       002_fixations_EXP_010.4.csv
    │   │       002_fixations_EXP_010.5.csv
    │   │       002_fixations_EXP_010.6.csv
    │   │       002_fixations_EXP_010.csv
    │   │       002_fixations_EXP_011.2.csv
    │   │       002_fixations_EXP_011.3.csv
    │   │       002_fixations_EXP_011.4.csv
    │   │       002_fixations_EXP_011.6.csv
    │   │       002_fixations_EXP_011.csv
    │   │
    │   └───saccades
    │           002_saccades_EXP_004.csv
    │           002_saccades_EXP_006.1.csv
    │           002_saccades_EXP_006.2.csv
    │           002_saccades_EXP_006.csv
    │           002_saccades_EXP_007.2.csv
    │           002_saccades_EXP_007.4.csv
    │           002_saccades_EXP_007.csv
    │           002_saccades_EXP_008.2.csv
    │           002_saccades_EXP_008.3.csv
    │           002_saccades_EXP_008.4.csv
    │           002_saccades_EXP_008.5.csv
    │           002_saccades_EXP_008.csv
    │           002_saccades_EXP_010.2.csv
    │           002_saccades_EXP_010.3.csv
    │           002_saccades_EXP_010.4.csv
    │           002_saccades_EXP_010.5.csv
    │           002_saccades_EXP_010.6.csv
    │           002_saccades_EXP_010.csv
    │           002_saccades_EXP_011.2.csv
    │           002_saccades_EXP_011.3.csv
    │           002_saccades_EXP_011.4.csv
    │           002_saccades_EXP_011.6.csv
    │           002_saccades_EXP_011.csv
    │
    ├───003
    │   ├───blinks
    │   │       003_blinks_EXP_013.2.csv
    │   │       003_blinks_EXP_013.3.csv
    │   │       003_blinks_EXP_013.4.csv
    │   │       003_blinks_EXP_013.5.csv
    │   │       003_blinks_EXP_013.csv
    │   │       003_blinks_EXP_014.2.csv
    │   │       003_blinks_EXP_014.3.csv
    │   │       003_blinks_EXP_014.4.csv
    │   │       003_blinks_EXP_014.5.csv
    │   │       003_blinks_EXP_014.csv
    │   │       003_blinks_EXP_015.2.csv
    │   │       003_blinks_EXP_015.3.csv
    │   │       003_blinks_EXP_015.csv
    │   │       003_blinks_EXP_019.csv
    │   │       003_blinks_EXP_13.10.csv
    │   │       003_blinks_EXP_13.7.csv
    │   │       003_blinks_EXP_13.8.csv
    │   │       003_blinks_EXP_13.9.csv
    │   │
    │   ├───ecg
    │   │       003_ecg_EXP_013.2.csv
    │   │       003_ecg_EXP_013.3.csv
    │   │       003_ecg_EXP_013.4.csv
    │   │       003_ecg_EXP_013.5.csv
    │   │       003_ecg_EXP_013.csv
    │   │       003_ecg_EXP_014.2.csv
    │   │       003_ecg_EXP_014.3.csv
    │   │       003_ecg_EXP_014.4.csv
    │   │       003_ecg_EXP_014.5.csv
    │   │       003_ecg_EXP_014.6.csv
    │   │       003_ecg_EXP_014.csv
    │   │       003_ecg_EXP_015.2.csv
    │   │       003_ecg_EXP_015.3.csv
    │   │       003_ecg_EXP_015.csv
    │   │       003_ecg_EXP_019.2.csv
    │   │       003_ecg_EXP_019.3.csv
    │   │       003_ecg_EXP_019.csv
    │   │       003_ecg_EXP_13.10.csv
    │   │       003_ecg_EXP_13.7.csv
    │   │       003_ecg_EXP_13.8.csv
    │   │       003_ecg_EXP_13.9.csv
    │   │
    │   ├───fixations
    │   │       003_fixations_EXP_013.2.csv
    │   │       003_fixations_EXP_013.3.csv
    │   │       003_fixations_EXP_013.4.csv
    │   │       003_fixations_EXP_013.5.csv
    │   │       003_fixations_EXP_013.csv
    │   │       003_fixations_EXP_014.2.csv
    │   │       003_fixations_EXP_014.3.csv
    │   │       003_fixations_EXP_014.4.csv
    │   │       003_fixations_EXP_014.5.csv
    │   │       003_fixations_EXP_014.6.csv
    │   │       003_fixations_EXP_014.csv
    │   │       003_fixations_EXP_015.2.csv
    │   │       003_fixations_EXP_015.3.csv
    │   │       003_fixations_EXP_015.csv
    │   │       003_fixations_EXP_019.2.csv
    │   │       003_fixations_EXP_019.3.csv
    │   │       003_fixations_EXP_019.csv
    │   │       003_fixations_EXP_13.10.csv
    │   │       003_fixations_EXP_13.7.csv
    │   │       003_fixations_EXP_13.8.csv
    │   │       003_fixations_EXP_13.9.csv
    │   │
    │   └───saccades
    │           003_saccades_EXP_013.2.csv
    │           003_saccades_EXP_013.3.csv
    │           003_saccades_EXP_013.4.csv
    │           003_saccades_EXP_013.5.csv
    │           003_saccades_EXP_013.csv
    │           003_saccades_EXP_014.2.csv
    │           003_saccades_EXP_014.3.csv
    │           003_saccades_EXP_014.4.csv
    │           003_saccades_EXP_014.5.csv
    │           003_saccades_EXP_014.6.csv
    │           003_saccades_EXP_014.csv
    │           003_saccades_EXP_015.2.csv
    │           003_saccades_EXP_015.3.csv
    │           003_saccades_EXP_015.csv
    │           003_saccades_EXP_019.2.csv
    │           003_saccades_EXP_019.3.csv
    │           003_saccades_EXP_019.csv
    │           003_saccades_EXP_13.10.csv
    │           003_saccades_EXP_13.7.csv
    │           003_saccades_EXP_13.8.csv
    │           003_saccades_EXP_13.9.csv
    │
    └───004
        ├───blinks
        │       004_blinks_EXP_016.10.csv
        │       004_blinks_EXP_016.2.csv
        │       004_blinks_EXP_016.3.csv
        │       004_blinks_EXP_016.5.csv
        │       004_blinks_EXP_016.7.csv
        │       004_blinks_EXP_016.8.csv
        │       004_blinks_EXP_016.9.csv
        │       004_blinks_EXP_016.csv
        │       004_blinks_EXP_017.2.csv
        │       004_blinks_EXP_017.csv
        │
        ├───ecg
        │       004_ecg_EXP_016.10.csv
        │       004_ecg_EXP_016.2.csv
        │       004_ecg_EXP_016.3.csv
        │       004_ecg_EXP_016.4.csv
        │       004_ecg_EXP_016.5.csv
        │       004_ecg_EXP_016.6.csv
        │       004_ecg_EXP_016.7.csv
        │       004_ecg_EXP_016.8.csv
        │       004_ecg_EXP_016.9.csv
        │       004_ecg_EXP_016.csv
        │       004_ecg_EXP_017.2.csv
        │       004_ecg_EXP_017.csv
        │
        ├───fixations
        │       004_fixations_EXP_016.10.csv
        │       004_fixations_EXP_016.2.csv
        │       004_fixations_EXP_016.3.csv
        │       004_fixations_EXP_016.4.csv
        │       004_fixations_EXP_016.5.csv
        │       004_fixations_EXP_016.6.csv
        │       004_fixations_EXP_016.7.csv
        │       004_fixations_EXP_016.8.csv
        │       004_fixations_EXP_016.9.csv
        │       004_fixations_EXP_016.csv
        │       004_fixations_EXP_017.2.csv
        │       004_fixations_EXP_017.3.csv
        │       004_fixations_EXP_017.csv
        │
        └───saccades
                004_saccades_EXP_016.10.csv
                004_saccades_EXP_016.2.csv
                004_saccades_EXP_016.3.csv
                004_saccades_EXP_016.4.csv
                004_saccades_EXP_016.5.csv
                004_saccades_EXP_016.6.csv
                004_saccades_EXP_016.7.csv
                004_saccades_EXP_016.8.csv
                004_saccades_EXP_016.9.csv
                004_saccades_EXP_016.csv
                004_saccades_EXP_017.2.csv
                004_saccades_EXP_017.3.csv
                004_saccades_EXP_017.csv

*This document was compiled from the two provided dataset papers/records and six data file excerpts. No information has been added beyond what is directly observable in those sources.*