# MAGI Dashboard — Full Implementation Plan

---

## 0. Design Decisions (Resolved)

The following decisions were confirmed by the project owner and **MUST** be followed throughout implementation:

| # | Decision | Resolution |
|---|----------|------------|
| 1 | **LLM Provider** | Google models only (Gemini/Gemma). No OpenAI/Anthropic/Ollama. |
| 2 | **Persistence** | SQLite database for simulation history, results, KPIs, agent traces. |
| 3 | **Multi-user** | Single-user desktop tool, but architect for **network sharing** (bind to `0.0.0.0`, optional auth, no hardcoded `localhost`). Possible future public hosting. |
| 4 | **Deployment** | `python -m magi --web` launches FastAPI + auto-opens browser. |
| 5 | **Branding** | Title = **"MAGI Dashboard"**. ALL branding is **configurable** (colors, logo, title, subtitle). Stored in settings. |
| 6 | **Theme** | **Light mode is default**. Dark mode available via toggle. Both themes must look professional. |
| 7 | **UI Philosophy** | Lightweight, fast, simple, professional. No visual bloat. Clean typography, ample whitespace, efficient data density. |
| 8 | **Configurability** | **Everything** configurable from the dashboard: agent cycle frequency/duration, system prompt, lean KG nodes/edges, distribution params, worker profiles, API keys, model selection, output paths, shortcuts, branding. |
| 9 | **Priority Order** | Phase 0 → 1 → 3 (2D viz) → 2 (KPIs) → 4 (Agent) → 5 (Lean KG) → 6 (Settings/Polish) |
| 10 | **Lean Shortcuts** | Pre-built: Muri/Fatigue, VSM, Ishikawa, 5 Whys, Line Balancing, OEE Breakdown. User can **add more via dashboard**. |
| 11 | **Codebase Refactoring** | Refactor existing code for modularity and configurability. Extract hardcoded values into configurable settings. |

---

## 1. Executive Summary

This plan describes the implementation of **MAGI Dashboard** — a lightweight, fast, professional web-based dashboard that provides total control over the MAGI (Manufacturing Agentive Generative Intelligence) framework. The dashboard replaces and extends the current CLI-based workflow with:

- **Real-time 2D visualization** of the Silverline assembly line (like Arena/AnyLogic)
- **Multi-simulation management** — run, queue, compare unlimited simulations
- **Full parameter control** — every ConfigState field, API keys, model selection, timing distributions
- **Live KPI dashboards** with charts, gauges, and time-series
- **Agent interaction** — chat with the Cognitive Agent, view reasoning traces
- **Lean Knowledge Graph visualization** — interactive, editable force-directed graph
- **Output management** — browse all artifacts, logs, CSVs, agent-generated files
- **Shortcut system** — quick-launch Lean analyses, pre-built prompts, scenario templates
- **SQLite persistence** — full simulation history, KPI comparison, agent trace archival
- **Configurable branding** — colors, logo, title, themes customizable from settings

---

## 2. Current Codebase Analysis

### 2.1 Architecture (4-Layer Stack)

| Layer | Module | Purpose | Key Classes |
|-------|--------|---------|-------------|
| L4 — Cognitive | `cognitive/agent.py` | LLM-based AI agent (Gemini) | `CognitiveAgent`, `AgentTraceEntry` |
| L4 — Cognitive | `cognitive/lean_kg.py` | Lean Knowledge Graph RAG | `LeanKGRetriever` |
| L4 — Cognitive | `cognitive/sandbox.py` | Sandboxed code execution | `CodeSandbox` |
| L3 — Digital | `digital/twin.py` | SimPy DES orchestrator | `DigitalTwin` |
| L3 — Digital | `digital/tool_api.py` | Agent→DT interface (11 tools) | `ToolAPI` |
| L3 — Digital | `digital/config.py` | Thread-safe config | `ConfigState` |
| L3 — Digital | `digital/models.py` | Data classes | `SimulationResult`, `TaskRecord`, `PhysioRecord` |
| L3 — Digital | `digital/kpi.py` | KPI computation | `KPIComputer` |
| L3 — Digital | `digital/processes.py` | SimPy generators | `_arrival_process`, `_cw_process`, `_mw_process` |
| L3 — Digital | `digital/replication.py` | Statistical experiments | `ReplicationRunner` |
| L2 — Edge | `edge/fatigue.py` | Fatigue classification | `FatigueMonitor` |
| L1 — Physical | `physical/constants.py` | Empirical parameters | Distribution params, physio baselines |
| L1 — Physical | `physical/samplers.py` | Stochastic sampling | `TaskDurationSampler`, `PhysiologicalSampler` |
| Meta | `meta/__init__.py` | Placeholder | Empty — **this is where we build** |
| Entry | `cli.py` | CLI experiment runner | `main()`, `_run_magi_simulation()` |

### 2.2 Data Flow (Current)

```
CLI args → DigitalTwin(ConfigState) → dt.run() → SimulationResult
                                         ↑ step_callback
                                    CognitiveAgent.monitor_cycle()
                                         ↓ tool calls
                                      ToolAPI → ConfigState mutations
```

### 2.3 Key Observations

1. **ConfigState** is already thread-safe (RLock) — ready for concurrent web access
2. **ToolAPI** returns JSON-serializable dicts — perfect for REST/WebSocket
3. **SimulationResult** has `.to_dataframe()` and `.summary()` — easy to serialize
4. **CognitiveAgent** maintains conversation history and trace — streamable to frontend
5. **LeanKG** data is static JSON (nodes.json, edges.json) — serve directly to frontend
6. **Processes** emit `TaskRecord`/`PhysioRecord` per event — streamable for live viz
7. **Meta layer** is explicitly reserved for web frontend (see `meta/__init__.py` docstring)

---

## 3. Technical Stack

### 3.1 Backend — FastAPI + WebSocket + SQLite

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Web Framework** | FastAPI | Async-native, WebSocket support, auto-generated OpenAPI docs, Pydantic validation |
| **WebSocket** | FastAPI WebSocket | Real-time streaming of simulation events, KPIs, agent messages |
| **Database** | SQLite (via `aiosqlite`) | Lightweight persistence for simulation history, KPIs, agent traces, settings |
| **Task Queue** | Python `asyncio` + `threading` | SimPy runs in threads; async bridge via `asyncio.Queue` |
| **Serialization** | Pydantic v2 models | Type-safe JSON serialization of all MAGI data classes |
| **Static Files** | FastAPI StaticFiles | Serve the frontend SPA |
| **CORS** | FastAPI CORSMiddleware | Dev-mode and network cross-origin support |

### 3.2 Frontend — Vite + React + TypeScript

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Build Tool** | Vite | Fast HMR, modern ESM bundling |
| **Framework** | React 19 + TypeScript | Component model ideal for dashboard panels |
| **Styling** | Vanilla CSS + CSS Variables | Full control, light/dark themes, configurable |
| **Charts** | Recharts | React-native charting, time-series, gauges |
| **2D Visualization** | HTML5 Canvas (custom) | Assembly line animation (conveyor, stations, workers) |
| **Graph Visualization** | D3.js force-directed | Lean KG interactive visualization |
| **State Management** | Zustand | Lightweight, TypeScript-first global state |
| **WebSocket Client** | Native WebSocket API | Real-time event streaming |
| **Icons** | Lucide React | Modern icon set |
| **Fonts** | Inter (Google Fonts) | Clean, professional typography |

### 3.3 Why NOT Next.js?

Next.js adds SSR complexity unnecessary for a local dashboard tool. Vite + React gives us:
- Faster dev server startup
- Simpler deployment (static build served by FastAPI)
- No SSR/hydration complexity
- Easier to host later (static assets + API server)

---

## 4. High-Level Architecture

```
┌──────────────────────────────────────────────────────┐
│                    MAGI Dashboard                    │
│                  (React SPA — Vite)                  │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│ Sim Ctrl │ 2D Viz   │ KPI Dash │ Agent    │ Lean KG  │
│ Panel    │ Canvas   │ Charts   │ Chat     │ Graph    │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
     │ REST     │ WS       │ WS       │ WS       │ REST
     ▼          ▼          ▼          ▼          ▼
┌──────────────────────────────────────────────────────┐
│              FastAPI Backend (Meta Layer)             │
├──────────────────────────────────────────────────────┤
│  REST API          │  WebSocket Hub                  │
│  /api/sim/*        │  /ws/simulation/{id}            │
│  /api/config/*     │  /ws/agent/{id}                 │
│  /api/lean/*       │                                 │
│  /api/settings/*   │  Broadcasts:                    │
│  /api/outputs/*    │  - task_record events            │
│                    │  - physio_record events           │
│                    │  - kpi_update snapshots           │
│                    │  - agent_message chunks           │
│                    │  - fatigue_alert events           │
├──────────────────────────────────────────────────────┤
│          Simulation Manager (Thread Pool)             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                │
│  │ Sim #1  │ │ Sim #2  │ │ Sim #N  │  (concurrent)  │
│  │ Thread  │ │ Thread  │ │ Thread  │                │
│  └────┬────┘ └────┬────┘ └────┬────┘                │
│       ▼           ▼           ▼                      │
│  DigitalTwin  DigitalTwin  DigitalTwin               │
│  + ToolAPI    + ToolAPI    + ToolAPI                  │
│  + Agent?     + Agent?     (baseline)                │
└──────────────────────────────────────────────────────┘
```


## 5. Backend Refactoring & API Design

### 5.1 New Module: `magi/meta/` (Meta Layer)

The `meta/` directory becomes the web backend. File structure:

```
magi/meta/
├── __init__.py            # Meta layer exports
├── server.py              # FastAPI app factory, startup/shutdown
├── routers/
│   ├── __init__.py
│   ├── simulation.py      # POST /run, GET /list, DELETE /stop, etc.
│   ├── config.py          # GET/PUT config, settings, API keys
│   ├── agent.py           # POST /chat, GET /trace
│   ├── lean.py            # GET /methods, GET /graph, GET /method/{id}
│   ├── outputs.py         # GET /files, GET /file/{path}, GET /kpis
│   └── shortcuts.py       # GET/POST prompt templates, lean analysis presets
├── websocket/
│   ├── __init__.py
│   ├── hub.py             # WebSocket connection manager, broadcasting
│   └── channels.py        # Per-simulation event channels
├── models/
│   ├── __init__.py
│   ├── requests.py        # Pydantic request schemas
│   ├── responses.py       # Pydantic response schemas
│   └── events.py          # WebSocket event schemas
├── services/
│   ├── __init__.py
│   ├── sim_manager.py     # Multi-simulation orchestrator
│   ├── db.py              # SQLite persistence layer (aiosqlite)
│   ├── settings_store.py  # Configurable settings (backed by SQLite)
│   └── event_bridge.py    # Thread→async event bridge
└── static/                # Built frontend files (after `npm run build`)
```

### 5.2 REST API Endpoints

#### Simulation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sim/run` | Start a new simulation (baseline or MAGI) |
| `POST` | `/api/sim/run-batch` | Start a batch of replications |
| `GET` | `/api/sim/list` | List all simulations (active + completed) |
| `GET` | `/api/sim/{id}` | Get simulation status and metadata |
| `GET` | `/api/sim/{id}/result` | Get completed simulation result (KPIs, config) |
| `GET` | `/api/sim/{id}/task-log` | Get task log as JSON array |
| `GET` | `/api/sim/{id}/physio-log` | Get physio log as JSON array |
| `POST` | `/api/sim/{id}/pause` | Pause a running simulation |
| `POST` | `/api/sim/{id}/resume` | Resume a paused simulation |
| `POST` | `/api/sim/{id}/speed` | Change simulation speed |
| `DELETE` | `/api/sim/{id}` | Stop and remove a simulation |
| `POST` | `/api/sim/compare` | Compare two simulation results |
| `POST` | `/api/sim/replications` | Run paired replications (baseline vs MAGI) |

#### Configuration & Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config/current` | Get current ConfigState snapshot |
| `PUT` | `/api/config/update` | Update ConfigState parameters |
| `GET` | `/api/config/defaults` | Get default parameter values and ranges |
| `GET` | `/api/settings` | Get global settings (API keys, model, output dir) |
| `PUT` | `/api/settings` | Update global settings |
| `GET` | `/api/settings/models` | List available LLM models |
| `GET` | `/api/config/workers` | Get worker profiles (physio baselines) |
| `GET` | `/api/config/distributions` | Get timing distribution parameters |
| `PUT` | `/api/config/distributions` | Override timing distributions |

#### Cognitive Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agent/{sim_id}/chat` | Send a message to the agent |
| `GET` | `/api/agent/{sim_id}/trace` | Get agent reasoning trace |
| `GET` | `/api/agent/{sim_id}/trace/summary` | Get trace summary |
| `POST` | `/api/agent/{sim_id}/tool` | Manually invoke a tool (bypass agent) |
| `GET` | `/api/agent/tools` | List available tools with schemas |

#### Lean Knowledge Graph

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/lean/graph` | Full graph (nodes + edges) for visualization |
| `GET` | `/api/lean/methods` | List all lean methods |
| `GET` | `/api/lean/method/{id}` | Full method detail with connected nodes |
| `GET` | `/api/lean/problems` | List all problem types |
| `POST` | `/api/lean/query` | Query KG by KPI state (same as agent's RAG) |

#### Outputs & Artifacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/outputs/files` | List all output files |
| `GET` | `/api/outputs/file/{path}` | Download a specific file |
| `GET` | `/api/outputs/images` | List generated images/plots |
| `DELETE` | `/api/outputs/file/{path}` | Delete an output file |

#### Shortcuts & Templates

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/shortcuts` | List all shortcuts (prompts, analyses) |
| `POST` | `/api/shortcuts` | Create a new shortcut |
| `POST` | `/api/shortcuts/{id}/execute` | Execute a shortcut |
| `DELETE` | `/api/shortcuts/{id}` | Delete a shortcut |

### 5.3 WebSocket Channels

#### `/ws/simulation/{sim_id}`

Real-time event stream for a running simulation:

```json
// Event types streamed:
{"type": "task_record", "data": {TaskRecord fields...}}
{"type": "physio_record", "data": {PhysioRecord fields...}}
{"type": "kpi_snapshot", "data": {KPI dict...}, "sim_time_s": 3600.0}
{"type": "config_changed", "data": {ConfigState snapshot...}}
{"type": "fatigue_alert", "data": {FatigueMonitor output...}}
{"type": "sim_progress", "progress_pct": 45.2, "sim_time_h": 3.6}
{"type": "sim_complete", "data": {SimulationResult summary...}}
{"type": "sim_error", "error": "..."}
{"type": "buffer_state", "cw_queue": 3, "mw_queue": 1}
```

#### `/ws/agent/{sim_id}`

Real-time agent communication stream:

```json
// Agent → Frontend
{"type": "agent_thinking", "text": "Analyzing KPIs..."}
{"type": "agent_response", "text": "I recommend...", "tool_calls": [...]}
{"type": "agent_tool_call", "tool": "set_robot_speed_factor", "args": {...}}
{"type": "agent_tool_result", "tool": "set_robot_speed_factor", "result": {...}}
{"type": "agent_file_created", "path": "...", "description": "..."}

// Frontend → Agent (via send)
{"type": "user_message", "text": "What's the current fatigue level?"}
{"type": "user_command", "command": "pause"}
```

### 5.4 SimulationManager Service

Core orchestrator that manages multiple concurrent simulations:

```python
class SimulationManager:
    """Manages multiple concurrent simulation runs with event streaming."""

    def __init__(self, settings: SettingsStore):
        self._simulations: Dict[str, SimulationSession] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=8)
        self._settings = settings

    async def start_simulation(self, request: SimRunRequest) -> str:
        """Launch a new simulation, return session ID."""

    async def stop_simulation(self, sim_id: str) -> None:
        """Gracefully stop a running simulation."""

    def get_session(self, sim_id: str) -> SimulationSession:
        """Get a simulation session by ID."""

    async def subscribe(self, sim_id: str) -> AsyncIterator[SimEvent]:
        """Async generator yielding real-time events from a simulation."""


@dataclass
class SimulationSession:
    id: str
    status: Literal["queued", "running", "paused", "completed", "error"]
    config: ConfigState
    digital_twin: DigitalTwin
    tool_api: Optional[ToolAPI]
    agent: Optional[CognitiveAgent]
    result: Optional[SimulationResult]
    event_queue: asyncio.Queue  # Thread→async bridge
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]  # user-defined labels, notes
```

### 5.5 Event Bridge (Thread → Async)

The critical bridge between SimPy's synchronous thread and FastAPI's async WebSocket:

```python
class EventBridge:
    """Bridges synchronous SimPy simulation events to async WebSocket streams."""

    def __init__(self, sim_id: str, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.sim_id = sim_id
        self._queue = event_queue
        self._loop = loop

    def emit(self, event_type: str, data: dict) -> None:
        """Called from simulation thread. Thread-safe push to async queue."""
        asyncio.run_coroutine_threadsafe(
            self._queue.put({"type": event_type, "data": data, "timestamp": time.time()}),
            self._loop
        )
```

### 5.6 Backend Refactoring Required in Existing Code

#### 5.6.1 `digital/processes.py` — Add Event Hooks

The SimPy processes need to emit events for real-time visualization. We add an optional `event_sink` callback parameter:

```python
# In _cw_process and _mw_process:
# After each TaskRecord is appended, also call:
if event_sink:
    event_sink("task_record", task_record_to_dict(tr))
    event_sink("physio_record", physio_record_to_dict(physio_rec))
```

#### 5.6.2 `digital/twin.py` — Add Event Sink Support

```python
def run(self, ..., event_sink: Optional[Callable] = None) -> SimulationResult:
    # Pass event_sink to process functions
    # Emit kpi_snapshot periodically (every N events)
    # Emit buffer_state after each put/get
```

#### 5.6.3 `digital/models.py` — Add Serialization

```python
@dataclass
class TaskRecord:
    # ... existing fields ...
    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable dict for WebSocket streaming."""

@dataclass
class SimulationResult:
    # ... existing fields ...
    def to_json(self) -> str:
        """Full JSON serialization."""
```

#### 5.6.4 `cognitive/agent.py` — Add Message Streaming

```python
class CognitiveAgent:
    def set_message_callback(self, callback: Callable[[str, str, dict], None]):
        """Set callback for streaming agent messages to frontend.
        callback(event_type, text, metadata)
        """
        self._message_callback = callback
```

#### 5.6.5 `cli.py` — Keep Intact

The CLI remains fully functional. The web server is a separate entry point (`python -m magi --web`).


## 6. Frontend Design & Feature Breakdown

### 6.1 Application Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  ◉ MAGI Dashboard              [Sim #1 ▼] [+ New Sim]    [⚙ ☾]  │  ← Top Bar
├───────┬─────────────────────────────────────────────────────────────┤
│       │                                                             │
│  📊   │   ┌─────────────────────────────────────────────────────┐  │
│  Dash  │   │           Active Content Area                       │  │
│       │   │   (switches based on sidebar selection)              │  │
│  🏭   │   │                                                      │  │
│  Sim   │   │   Dashboard / Simulation / Agent / Lean / ...       │  │
│       │   │                                                      │  │
│  🤖   │   └─────────────────────────────────────────────────────┘  │
│  Agent │                                                            │
│       │   ┌─────────────────────────────────────────────────────┐  │
│  📈   │   │  Bottom Panel (collapsible)                         │  │
│  KPIs  │   │  Console / Alerts / Agent Trace / Logs             │  │
│       │   └─────────────────────────────────────────────────────┘  │
│  🔗   │                                                            │
│  Lean  │                                                            │
│       │                                                            │
│  📁   │                                                            │
│  Files │                                                            │
│       │                                                            │
│  ⚙    │                                                            │
│  Config│                                                            │
│       │                                                            │
└───────┴─────────────────────────────────────────────────────────────┘
```

### 6.2 Page Descriptions

#### Page 1: Dashboard (Home) — `📊`

**Overview panel** with live summary of all active simulations:

- **Active Simulations Card Grid** — Each card shows: name, status badge (Running/Paused/Complete), progress bar, elapsed time, throughput gauge
- **System Health Strip** — CPU usage, memory, active threads
- **Quick Actions** — "New Baseline Run", "New MAGI Run", "Run Full Experiment" buttons
- **Recent Results** — Table of last 10 completed simulations with key KPIs
- **Alerts Feed** — Real-time fatigue alerts, errors, agent notifications

#### Page 2: Simulation Control & 2D Visualization — `🏭`

The centerpiece. Split into two zones:

**Top: 2D Assembly Line Visualization (HTML5 Canvas)**

```
 ┌─ Conveyor In ─────────────────────────────────────────────── Conveyor Out ─┐
 │                                                                              │
 │   📦→  [Buffer]  →  ┌──────────────┐  →  [Buffer]  →  ┌───────────┐  → 📦  │
 │   ···      ⬜⬜⬜    │  CW Station   │       ⬜⬜⬜     │ MW Station │        │
 │                     │  👷 Worker 001 │                  │ 👷 W. 001 │        │
 │                     │  🤖 Robot Arm  │                  │           │        │
 │                     │  [Phase 3/5]  │                  │ [Phase 1] │        │
 │                     └──────────────┘                  └───────────┘        │
 │                                                                              │
 │  Product #47 ████████░░ 65%    Speed: 120x    Time: 3h 24m / 8h 00m        │
 └──────────────────────────────────────────────────────────────────────────────┘
```

Visual elements (animated on Canvas):
- **Conveyor belt** — animated horizontal belt with product boxes moving left→right
- **CW Station** — Worker avatar + Robot arm icon, color-coded by current phase
- **MW Station** — Worker avatar, color-coded by fatigue level
- **Inter-station buffers** — Visual queue showing items waiting (boxes in/out)
- **Product flow** — Products animate from conveyor → CW → buffer → MW → output
- **Phase indicators** — Each station shows current task phase with progress arc
- **Color coding** — Green (normal), Yellow (elevated fatigue), Red (critical)
- **Worker HR overlay** — Small heart icon with BPM number, pulses at rate
- **Statistics overlay** — Live counters: produced, dropped, queue length

**Bottom: Simulation Controls**

- **Control Bar**: ▶ Play │ ⏸ Pause │ ⏹ Stop │ Speed slider (0.1x–10000x) │ Time display
- **Parameter Panel** (collapsible sidebar):
  - Robot Speed Factor: slider [0.5, 2.0] with live preview
  - Takt Time: slider [20s, 300s] with throughput calculator
  - Buffer Capacity: slider [1, 20]
  - CW Worker: dropdown (001–004) with physio profile preview
  - MW Worker: dropdown (001–004) with physio profile preview
  - Jitter CV: slider [0, 0.3]
- **Apply Changes** button (updates ConfigState in real-time mid-simulation)

#### Page 3: KPI Dashboard — `📈`

Rich visual KPI monitoring with multiple chart types:

**Row 1: Gauge Cards** (4 large circular gauges)
- Throughput (units/hr) — needle gauge with target zone
- OEE — percentage ring with color gradient
- Line Balance Ratio — balance beam visualization
- Mean Fatigue Score — human-centric gauge (green→red gradient)

**Row 2: Time-Series Charts** (2 columns)
- Left: HR over time (CW + MW overlaid), with CTRL baseline horizontal line
- Right: Fatigue score over time, with warning/critical threshold lines

**Row 3: Comparative Bar Charts**
- CW vs MW cycle times (grouped bars)
- Station utilization comparison (CW, MW, Robot)
- PLI comparison (CW vs MW)

**Row 4: Distribution Plots**
- CW cycle time histogram
- MW cycle time histogram
- Buffer wait time distribution

**Row 5: KPI Summary Table**
- All ~25 KPIs in a sortable, filterable table
- Delta column (% change from baseline) with color-coded arrows
- Sparkline trend for each KPI across replications

#### Page 4: Agent Interface — `🤖`

**Chat Panel** (left 60%):
- Full chat interface with the Cognitive Agent
- Message bubbles: user (right, blue), agent (left, dark)
- Inline rendering of tool calls (collapsible cards showing tool name, args, result)
- File previews for agent-generated images/plots (inline thumbnail)
- Typing indicator when agent is processing
- Pre-built prompt buttons at bottom:
  - "Analyze current KPIs"
  - "Check fatigue levels"
  - "Suggest optimizations"
  - "Generate Ishikawa diagram"
  - "Run what-if: speed +20%"
  - "Create VSM for current state"
  - Custom prompt input

**Trace Panel** (right 40%):
- Timeline view of all agent monitoring cycles
- Each cycle shows: sim time, trigger type (auto/user/fatigue), tools used
- Expandable: full reasoning text, tool call details, files created
- Filter by trigger type
- Export trace as JSON

#### Page 5: Lean Knowledge Graph — `🔗`

**Interactive Force-Directed Graph** (D3.js):

- **Nodes**: Lean methods (blue circles), Problem types (red diamonds), KPIs (green squares)
- **Edges**: ADDRESSES (solid), RELATES_TO (dashed), IMPACTS (dotted)
- **Interactions**: Click node → detail panel, hover → highlight connections, drag to reposition
- **Search**: Filter nodes by name, category, or type
- **Zoom**: Mouse wheel zoom + pan
- **Layout**: Force-directed with collision avoidance

**Detail Panel** (slides out on click):
- Full method description
- Trigger conditions (formatted as rules)
- Expected KPI impacts (with magnitude bars)
- Simulation adjustments (actionable — "Apply" button sends to ToolAPI)
- Connected nodes list
- References

**Quick Analysis Shortcuts**:
- "Run Muri Analysis" — queries KG with current KPIs, highlights triggered methods
- "Show Bottleneck Methods" — filters to methods addressing throughput/cycle time
- "Show Ergonomic Methods" — filters to methods addressing fatigue/PLI

#### Page 6: Outputs & Files — `📁`

- **File Browser**: Tree view of `magi_outputs/` directory
- **Preview Panel**: CSV viewer (table), JSON viewer (syntax highlighted), Image viewer, Plot viewer
- **Actions**: Download, Delete, Open in new tab
- **Comparison View**: Side-by-side comparison of two simulation results
- **Export**: Download all outputs as ZIP

#### Page 7: Settings & Configuration — `⚙`

**General Settings**:
- Output directory path
- Default simulation duration
- Default replications count
- Default random seed
- Server host/port (for network sharing)

**Branding & Appearance**:
- Dashboard title (default: "MAGI Dashboard")
- Dashboard subtitle
- Logo URL (optional)
- Primary accent color picker
- Theme toggle (light/dark, default: light)
- Custom CSS override textarea

**LLM Configuration** (Google only):
- API Key input (masked) — stored in SQLite settings
- Model selector (dropdown: gemini-2.5-flash, gemini-2.5-pro, gemma-4-31b-it, etc.)
- Temperature slider
- Custom model name input

**Agent Configuration**:
- System prompt (full textarea, editable)
- Monitoring cycle interval (seconds) — how often agent checks KPIs
- Monitoring cycle duration limit (seconds)
- Max tool calls per cycle
- Auto-monitoring on/off toggle
- Fatigue alert threshold (configurable trigger level)

**Distribution Parameters**:
- Editable table of all CW_TIMING_PARAMS and MW_TIMING_PARAMS
- Distribution type dropdown (norm, gamma, expon, lognorm, constant)
- Parameter fields (shape, loc, scale, mean, std_dev)
- Import from JSON button
- Reset to defaults button

**Worker Profiles**:
- View/edit PHYSIO_HR_BASELINES table
- View/edit PHYSIO_CTRL_HR values
- View/edit PHYSIO_IBI_BASELINES table
- Add/remove worker profiles

**Lean KG Editor**:
- Add/edit/delete lean method nodes
- Add/edit/delete problem type nodes
- Add/edit/delete KPI nodes
- Add/edit/delete edges (relationships)
- Import/export KG as JSON
- Reset to defaults button

**Shortcuts Manager**:
- Create/edit/delete prompt templates
- Create/edit/delete lean analysis presets
- Import/export shortcuts as JSON

### 6.3 Design System

#### Color Palette (Light Theme — DEFAULT)

```css
:root {
  /* Light theme (default) */
  --bg-primary:      hsl(220, 20%, 97%);   /* Near-white background */
  --bg-secondary:    hsl(220, 18%, 100%);  /* Card backgrounds (white) */
  --bg-tertiary:     hsl(220, 16%, 94%);   /* Elevated surfaces */
  --border:          hsl(220, 15%, 85%);   /* Subtle borders */
  --text-primary:    hsl(220, 20%, 12%);   /* Primary text (near-black) */
  --text-secondary:  hsl(220, 10%, 45%);   /* Secondary text */
  --accent-blue:     hsl(217, 91%, 50%);   /* Primary actions */
  --accent-cyan:     hsl(187, 85%, 40%);   /* Data/charts */
  --accent-green:    hsl(142, 71%, 38%);   /* Success/healthy */
  --accent-amber:    hsl(38, 92%, 45%);    /* Warning/elevated */
  --accent-red:      hsl(0, 84%, 50%);     /* Critical/error */
  --accent-purple:   hsl(262, 83%, 55%);   /* Agent/AI elements */
  --shadow:          0 1px 3px rgba(0,0,0,0.08);  /* Card shadows */
}

/* Dark theme (toggle) */
[data-theme="dark"] {
  --bg-primary:      hsl(220, 20%, 8%);
  --bg-secondary:    hsl(220, 18%, 12%);
  --bg-tertiary:     hsl(220, 16%, 16%);
  --border:          hsl(220, 15%, 22%);
  --text-primary:    hsl(220, 10%, 92%);
  --text-secondary:  hsl(220, 10%, 60%);
  --accent-blue:     hsl(217, 91%, 60%);
  --accent-cyan:     hsl(187, 85%, 53%);
  --accent-green:    hsl(142, 71%, 45%);
  --accent-amber:    hsl(38, 92%, 50%);
  --accent-red:      hsl(0, 84%, 60%);
  --accent-purple:   hsl(262, 83%, 62%);
  --shadow:          0 1px 3px rgba(0,0,0,0.3);
}
```

**IMPORTANT**: All accent colors are **configurable** via the Settings page and stored in `SettingsStore`. The CSS variables above are defaults. The branding section in Settings allows overriding `--accent-blue`, the dashboard title, logo URL, and subtitle.

#### Typography

```css
--font-sans: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;
```

#### Component Patterns

- **Cards**: `bg-secondary` with 1px `border`, 8px border-radius, subtle `box-shadow`
- **Micro-animations**: 150ms ease-out transitions on interactive elements (keep it fast)
- **Hover effects**: Subtle border-color change + slight elevation on cards
- **Status badges**: Pill-shaped with color-coded backgrounds
- **Charts**: Consistent color scheme, tooltips on hover
- **No glassmorphism in light mode** — clean flat cards with borders. Dark mode may use subtle glass effects.


## 7. Implementation Phases

### Phase 0: Foundation (Backend Skeleton + Dev Tooling)
**Estimated: ~2 hours**

1. Install backend dependencies: `fastapi`, `uvicorn`, `websockets`, `aiosqlite`, `python-dotenv`
2. Create `magi/meta/` module structure (all `__init__.py` files)
3. Create FastAPI app factory in `meta/server.py` (bind `0.0.0.0` by default)
4. Add `--web` flag to `__main__.py` → launches `uvicorn` + auto-opens browser
5. Create SQLite database layer (`db.py`) with tables: simulations, kpi_snapshots, agent_traces, settings
6. Create `SettingsStore` backed by SQLite (branding, API keys, agent config, defaults)
7. Set up Vite + React + TypeScript project in `magi/frontend/`
8. Configure proxy from Vite dev server → FastAPI backend
9. Create base CSS design system (light theme default, dark theme toggle, CSS variables)
10. Create shell layout (sidebar, top bar, content area, bottom panel)
11. Implement theme toggle (light/dark) with `data-theme` attribute on `<html>`

### Phase 1: Core Backend APIs + Simulation Manager
**Estimated: ~3 hours**

1. Implement `SimulationManager` service with thread pool
2. Implement `EventBridge` (sync thread → async queue)
3. Refactor `digital/twin.py` — add `event_sink` parameter to `run()`
4. Refactor `digital/processes.py` — emit events from SimPy generators
5. Add `.to_dict()` methods to `TaskRecord`, `PhysioRecord`, `SimulationResult`
6. Implement REST routers: `simulation.py`, `config.py`
7. Implement WebSocket hub + `/ws/simulation/{id}` channel
8. Test: start simulation via REST, receive events via WebSocket

### Phase 2: Dashboard Home + KPI Visualization
**Estimated: ~3 hours**

1. Build Dashboard home page component
2. Build simulation card grid (active + completed)
3. Implement KPI gauge components (throughput, OEE, fatigue, balance)
4. Build time-series chart components (HR, fatigue over sim time)
5. Build bar chart components (utilization, cycle times)
6. Wire WebSocket KPI streaming to chart state
7. Build KPI summary table with delta coloring
8. Build alerts feed component

### Phase 3: 2D Assembly Line Visualization
**Estimated: ~4 hours**

1. Design Canvas layout for Silverline line (conveyor, stations, buffers)
2. Implement product entity animation (spawn → CW → buffer → MW → exit)
3. Implement CW station visualization (5-phase cycle indicator)
4. Implement MW station visualization (2-phase cycle indicator)
5. Implement robot arm animation (visual check + grounding test)
6. Implement buffer queue visualization (product boxes stacking)
7. Add worker avatars with HR/fatigue color overlay
8. Wire WebSocket `task_record` events to animation state machine
9. Add simulation controls bar (play/pause/stop/speed)
10. Add parameter adjustment sidebar with live ConfigState updates

### Phase 4: Agent Chat Interface
**Estimated: ~3 hours**

1. Implement `/api/agent/{sim_id}/chat` endpoint
2. Implement `/ws/agent/{sim_id}` WebSocket channel
3. Refactor `CognitiveAgent` — add message callback for streaming
4. Build chat UI component (message list, input, send button)
5. Build tool call visualization (inline cards showing name/args/result)
6. Build pre-built prompt buttons (quick actions)
7. Build agent trace timeline view
8. Build file preview for agent-generated artifacts

### Phase 5: Lean Knowledge Graph Visualization
**Estimated: ~3 hours**

1. Implement `/api/lean/graph` endpoint (serves nodes.json + edges.json)
2. Build D3.js force-directed graph component
3. Implement node styling by type (method=circle, problem=diamond, kpi=square)
4. Implement edge styling by relation type
5. Build detail panel (slides out on node click)
6. Add search/filter functionality
7. Add "Apply" buttons in detail panel → ToolAPI calls
8. Build shortcut buttons (Muri Analysis, Bottleneck, Ergonomic)
9. Implement KG query endpoint → highlights triggered methods

### Phase 6: Settings, Outputs & Polish
**Estimated: ~3 hours**

1. Build Settings page (API keys, model, distributions, worker profiles)
2. Build file browser for outputs directory
3. Build file previewer (CSV table, JSON tree, image viewer)
4. Build comparison view (side-by-side KPIs with delta table)
5. Build shortcuts manager (create/edit/delete prompt templates)
6. Add keyboard shortcuts (Ctrl+N new sim, Space pause, etc.)
7. Add responsive layout adjustments
8. Final polish: animations, transitions, loading states, error handling
9. Build production bundle + serve from FastAPI

---

## 8. File Manifest (Complete)

### 8.1 Backend Files (New)

```
magi/meta/
├── __init__.py                    # Meta layer exports, VERSION
├── server.py                      # FastAPI app, startup/shutdown, CORS, static
├── routers/
│   ├── __init__.py
│   ├── simulation.py              # ~200 lines — sim CRUD + control
│   ├── config.py                  # ~120 lines — config + settings endpoints
│   ├── agent.py                   # ~150 lines — chat + trace endpoints
│   ├── lean.py                    # ~100 lines — KG endpoints
│   ├── outputs.py                 # ~80 lines  — file browser endpoints
│   └── shortcuts.py               # ~80 lines  — shortcut CRUD
├── websocket/
│   ├── __init__.py
│   ├── hub.py                     # ~120 lines — connection manager
│   └── channels.py                # ~80 lines  — per-sim channels
├── models/
│   ├── __init__.py
│   ├── requests.py                # ~100 lines — Pydantic request schemas
│   ├── responses.py               # ~120 lines — Pydantic response schemas
│   └── events.py                  # ~60 lines  — WebSocket event schemas
├── services/
│   ├── __init__.py
│   ├── sim_manager.py             # ~250 lines — multi-sim orchestrator
│   ├── db.py                      # ~150 lines — SQLite schema + CRUD
│   ├── settings_store.py          # ~120 lines — configurable settings (SQLite-backed)
│   └── event_bridge.py            # ~60 lines  — thread→async bridge
```

### 8.2 Frontend Files (New)

```
magi/frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx                   # React entry point
│   ├── App.tsx                    # Root component with routing
│   ├── index.css                  # Design system + global styles
│   ├── api/
│   │   ├── client.ts              # Fetch wrapper for REST API
│   │   ├── websocket.ts           # WebSocket connection manager
│   │   └── types.ts               # TypeScript interfaces matching Pydantic
│   ├── store/
│   │   ├── simulationStore.ts     # Zustand store for sim state
│   │   ├── agentStore.ts          # Zustand store for agent chat
│   │   ├── settingsStore.ts       # Zustand store for settings
│   │   └── kpiStore.ts            # Zustand store for live KPIs
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   ├── BottomPanel.tsx
│   │   │   └── ContentArea.tsx
│   │   ├── sim/
│   │   │   ├── SimCard.tsx
│   │   │   ├── SimControls.tsx
│   │   │   ├── ParamPanel.tsx
│   │   │   └── SimSetupModal.tsx
│   │   ├── viz/
│   │   │   ├── AssemblyLineCanvas.tsx   # 2D production line visualization
│   │   │   ├── ConveyorBelt.ts          # Canvas drawing: conveyor animation
│   │   │   ├── StationRenderer.ts       # Canvas drawing: CW/MW stations
│   │   │   ├── ProductEntity.ts         # Canvas drawing: product flow
│   │   │   └── WorkerOverlay.ts         # Canvas drawing: worker status
│   │   ├── kpi/
│   │   │   ├── GaugeCard.tsx
│   │   │   ├── TimeSeriesChart.tsx
│   │   │   ├── BarChart.tsx
│   │   │   ├── KpiTable.tsx
│   │   │   └── DistributionPlot.tsx
│   │   ├── agent/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── ToolCallCard.tsx
│   │   │   ├── PromptButtons.tsx
│   │   │   └── TraceTimeline.tsx
│   │   ├── lean/
│   │   │   ├── KnowledgeGraph.tsx       # D3.js force-directed graph
│   │   │   ├── MethodDetail.tsx
│   │   │   ├── GraphControls.tsx
│   │   │   └── AnalysisShortcuts.tsx
│   │   ├── settings/
│   │   │   ├── GeneralSettings.tsx
│   │   │   ├── BrandingSettings.tsx     # Title, logo, accent color, theme
│   │   │   ├── LlmSettings.tsx
│   │   │   ├── AgentSettings.tsx        # System prompt, cycle config
│   │   │   ├── DistributionEditor.tsx
│   │   │   ├── WorkerProfileEditor.tsx
│   │   │   ├── LeanKgEditor.tsx         # Add/edit/delete KG nodes/edges
│   │   │   └── ShortcutManager.tsx
│   │   ├── outputs/
│   │   │   ├── FileBrowser.tsx
│   │   │   ├── FilePreview.tsx
│   │   │   └── ComparisonView.tsx
│   │   └── common/
│   │       ├── StatusBadge.tsx
│   │       ├── Slider.tsx
│   │       ├── Modal.tsx
│   │       ├── Tooltip.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── AlertCard.tsx
│   └── pages/
│       ├── DashboardPage.tsx
│       ├── SimulationPage.tsx
│       ├── KpiPage.tsx
│       ├── AgentPage.tsx
│       ├── LeanPage.tsx
│       ├── OutputsPage.tsx
│       └── SettingsPage.tsx
```

### 8.3 Modified Existing Files

| File | Change | Scope |
|------|--------|-------|
| `__main__.py` | Add `--web`, `--host`, `--port` flags → launch FastAPI server | ~15 lines |
| `digital/twin.py` | Add `event_sink` param to `run()` | ~20 lines |
| `digital/processes.py` | Emit events from SimPy generators | ~15 lines |
| `digital/models.py` | Add `.to_dict()` methods | ~30 lines |
| `cognitive/agent.py` | Configurable system prompt, model, temp; add message callback | ~40 lines |
| `cognitive/lean_kg.py` | Add CRUD methods; load from SQLite if available | ~30 lines |
| `physical/constants.py` | Make distributions overridable via settings | ~10 lines |
| `meta/__init__.py` | Replace placeholder with real exports | 10 lines |

---

## 9. Dependencies

### 9.1 Backend (Python)

```
# Add to requirements.txt / pyproject.toml
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
websockets>=13.0
pydantic>=2.0
python-multipart>=0.0.9
aiofiles>=24.1.0
aiosqlite>=0.20.0
```

### 9.2 Frontend (Node.js)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "recharts": "^2.15.0",
    "d3": "^7.9.0",
    "zustand": "^5.0.0",
    "lucide-react": "^0.460.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/d3": "^7.4.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.6.0",
    "vite": "^6.0.0"
  }
}
```

---

## 10. Configurability Manifest

The following parameters MUST be configurable from the Settings page at runtime. They are persisted in SQLite and loaded on startup.

### 10.1 Agent Configuration (currently hardcoded in `cognitive/agent.py`)

| Parameter | Current Location | Default | Configurable Via |
|-----------|-----------------|---------|------------------|
| System prompt | `CognitiveAgent.__init__` | Hardcoded string | Settings > Agent > System Prompt textarea |
| Monitor cycle interval | `cli.py` step_callback timing | ~60s sim time | Settings > Agent > Cycle Interval slider |
| Max tool calls per cycle | `CognitiveAgent.monitor_cycle` | 5 | Settings > Agent > Max Tool Calls |
| LLM model name | `CognitiveAgent.__init__` | `gemini-2.5-flash` | Settings > LLM > Model dropdown |
| LLM temperature | `CognitiveAgent.__init__` | 0.3 | Settings > LLM > Temperature slider |
| API key | Environment variable | `GOOGLE_API_KEY` | Settings > LLM > API Key input |

### 10.2 Simulation Configuration (currently in `ConfigState` + `constants.py`)

| Parameter | Default | Configurable Via |
|-----------|---------|------------------|
| All `ConfigState` fields | See `config.py` | Simulation > Parameter Panel sliders |
| CW/MW timing distributions | `CW_TIMING_PARAMS`, `MW_TIMING_PARAMS` | Settings > Distributions table |
| Worker physio baselines | `PHYSIO_HR_BASELINES` | Settings > Worker Profiles editor |
| Fatigue model coefficients | `PhysiologicalSampler` constants | Settings > Advanced > Fatigue Model |

### 10.3 Lean KG (currently static JSON files)

| Parameter | Configurable Via |
|-----------|------------------|
| Method nodes (add/edit/delete) | Settings > Lean KG Editor |
| Problem nodes (add/edit/delete) | Settings > Lean KG Editor |
| KPI nodes (add/edit/delete) | Settings > Lean KG Editor |
| Edges/relationships | Settings > Lean KG Editor |
| Full KG export/import | Settings > Lean KG Editor > Import/Export JSON |

### 10.4 Branding & UI

| Parameter | Default | Configurable Via |
|-----------|---------|------------------|
| Dashboard title | "MAGI Dashboard" | Settings > Branding > Title |
| Dashboard subtitle | "" | Settings > Branding > Subtitle |
| Logo URL | None | Settings > Branding > Logo URL |
| Primary accent color | `hsl(217, 91%, 50%)` | Settings > Branding > Color picker |
| Theme | Light | Top bar toggle |

---

## 11. Codebase Refactoring Requirements

Before building the dashboard, the following refactoring is needed to make the existing code configurable:

### 11.1 `cognitive/agent.py`
- Extract the system prompt into a configurable parameter (passed via constructor or settings)
- Extract the LLM model name and temperature into constructor parameters
- Add `set_message_callback()` for streaming agent messages to WebSocket
- Make monitor cycle interval configurable (currently implicit in step_callback timing)
- Add max_tool_calls_per_cycle parameter

### 11.2 `digital/twin.py`
- Add `event_sink: Optional[Callable]` parameter to `run()`
- Emit events for each task completion, physio record, buffer state change
- Emit periodic KPI snapshots (configurable interval)

### 11.3 `digital/processes.py`
- Add `event_sink` parameter to `_arrival_process`, `_cw_process`, `_mw_process`
- Emit `task_record` and `physio_record` events after each phase
- Emit `buffer_state` events on buffer put/get

### 11.4 `digital/models.py`
- Add `.to_dict()` methods to `TaskRecord`, `PhysioRecord`, `SimulationResult`
- Add `.to_json()` method to `SimulationResult`

### 11.5 `physical/constants.py`
- Keep as defaults but make values overridable via SettingsStore
- Load from SQLite on startup, fall back to hardcoded defaults

### 11.6 `cognitive/lean_kg.py`
- Load KG data from SQLite if available, fall back to JSON files
- Add methods to add/update/delete nodes and edges

### 11.7 `cli.py`
- Keep fully intact and functional
- `python -m magi` still runs the CLI as before

### 11.8 `__main__.py`
- Add `--web` flag: `python -m magi --web` launches the dashboard
- Add `--host` and `--port` optional args for network binding
