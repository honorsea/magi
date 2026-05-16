# MAGI Dashboard — Implementation Directives

> **Target Audience**: You are an LLM coding agent tasked with implementing the MAGI Dashboard.
> **Authoritative Specification**: `implementation.md` in the `magi/` project root. Read it FULLY before writing any code.

---

## MANDATORY RULES

1. **Read `implementation.md` completely** before starting. It contains the full architecture, API design, file manifest, design system, and configurability requirements.
2. **Read every existing source file** in the `magi/` package before modifying anything. The codebase is a working, tested system. Breaking existing functionality is UNACCEPTABLE.
3. **`python -m magi` must continue to work** exactly as before. The CLI is untouched. Only `python -m magi --web` launches the dashboard.
4. **Light mode is the DEFAULT theme**. Dark mode is secondary, available via toggle.
5. **Google models ONLY** for LLM. No OpenAI, Anthropic, or Ollama abstractions.
6. **SQLite for persistence**. No JSON file stores. Use `aiosqlite` for async access.
7. **Everything is configurable** from the dashboard UI. See Section 10 of `implementation.md` for the full configurability manifest.
8. **Lightweight, fast, simple, professional**. No visual bloat, no heavy animations, no unnecessary dependencies.
9. **Do NOT delete or rewrite existing files wholesale**. Make surgical, additive changes. Add `event_sink` parameters, `to_dict()` methods, and constructor parameters — do not restructure class hierarchies.
10. **All branding is configurable**. Title, subtitle, logo, colors stored in SettingsStore and loaded by the frontend on startup.
11. **Do NOT try to implement entire phases at once**. Implement step by step, if you try to implement everything at once, you will exceed the maximum output token limit and fail to complete the task.
12. **Do not generate all code at once**. Generate code in small, manageable chunks.

---

## IMPLEMENTATION SEQUENCE

Follow the phases in this exact order. Each phase must be **fully working** before moving to the next.

### Phase 0: Foundation
**Goal**: FastAPI server boots, React app renders, theme toggle works.

1. Install Python deps: `pip install fastapi uvicorn[standard] websockets aiosqlite pydantic python-multipart aiofiles`
2. Create `magi/meta/` directory structure per Section 5.1 of `implementation.md`
3. Implement `meta/services/db.py`:
   - SQLite database with tables: `simulations`, `kpi_snapshots`, `agent_traces`, `settings`, `shortcuts`, `lean_kg_overrides`
   - Auto-create on first run. Store DB file in `magi_data/magi.db`
4. Implement `meta/services/settings_store.py`:
   - Load/save all settings from SQLite `settings` table
   - Default values for branding, agent config, LLM config, distributions
   - Thread-safe reads (settings are read-heavy)
5. Implement `meta/server.py`:
   - FastAPI app factory with CORS (allow all origins in dev)
   - Mount static files from `meta/static/` (for production build)
   - Bind to `0.0.0.0` by default (network-shareable)
   - Include all routers
6. Update `__main__.py`:
   - Add `--web` flag (launches uvicorn + opens browser)
   - Add `--host` (default `0.0.0.0`) and `--port` (default `8765`) args
   - `python -m magi` without `--web` runs CLI as before
7. Scaffold React app in `magi/frontend/`:
   - `npx -y create-vite@latest ./ --template react-ts` (run with `--help` first)
   - Install: `react-router-dom`, `recharts`, `d3`, `zustand`, `lucide-react`
   - Configure `vite.config.ts` with proxy to `http://localhost:8765`
8. Create `src/index.css` with BOTH light (default) and dark theme CSS variables per Section 6.3
9. Create shell layout: `Sidebar.tsx`, `TopBar.tsx`, `ContentArea.tsx`, `BottomPanel.tsx`
10. Implement theme toggle: `data-theme` attribute on `<html>`, toggle button in TopBar
11. Verify: `python -m magi --web` opens browser to working shell layout

### Phase 1: Core Backend APIs + Simulation Manager
**Goal**: Start a simulation via REST API, receive real-time events via WebSocket.

1. Add `event_sink` parameter to `digital/processes.py` functions (`_arrival_process`, `_cw_process`, `_mw_process`). After each `TaskRecord`/`PhysioRecord` is appended to logs, also call `event_sink(event_type, data_dict)` if provided.
2. Add `event_sink` parameter to `digital/twin.py` `run()` method. Pass it down to process functions. Emit `kpi_snapshot` every 50 task completions. Emit `sim_progress` every 100 sim-time seconds.
3. Add `.to_dict()` methods to `TaskRecord`, `PhysioRecord`, `SimulationResult` in `digital/models.py`. Must be JSON-serializable (no numpy types, no dataclass nesting — flatten PhysioRecord inside TaskRecord).
4. Implement `meta/services/event_bridge.py` — thread-safe bridge using `asyncio.run_coroutine_threadsafe`.
5. Implement `meta/services/sim_manager.py` — manages `SimulationSession` objects, thread pool, event queues.
6. Implement `meta/routers/simulation.py` — all endpoints from Section 5.2.
7. Implement `meta/routers/config.py` — ConfigState CRUD + settings endpoints.
8. Implement `meta/websocket/hub.py` + `channels.py` — WebSocket connection manager.
9. Persist completed simulation results to SQLite.
10. Verify: `curl POST /api/sim/run` starts simulation, WebSocket `/ws/simulation/{id}` streams events.

### Phase 2: Dashboard Home + KPI Visualization
**Goal**: Dashboard page shows simulation cards, live KPI gauges, and charts.

1. Implement `src/api/client.ts` (fetch wrapper) and `src/api/websocket.ts` (WS manager)
2. Implement `src/api/types.ts` — TypeScript interfaces matching all Pydantic models
3. Implement Zustand stores: `simulationStore.ts`, `kpiStore.ts`
4. Build `DashboardPage.tsx`: simulation cards grid, quick action buttons, recent results table
5. Build KPI components: `GaugeCard.tsx`, `TimeSeriesChart.tsx`, `BarChart.tsx`, `KpiTable.tsx`
6. Build `KpiPage.tsx` with all chart rows per Section 6.2
7. Wire WebSocket KPI streaming to Zustand store → React re-renders
8. Build `SimSetupModal.tsx` for creating new simulations

### Phase 3: 2D Assembly Line Visualization
**Goal**: Real-time animated Canvas showing products flowing through CW → MW.

1. Build `AssemblyLineCanvas.tsx` — main Canvas component with `requestAnimationFrame` loop
2. Implement `ConveyorBelt.ts` — animated belt drawing
3. Implement `StationRenderer.ts` — CW station (5-phase indicator), MW station (2-phase indicator), robot arm
4. Implement `ProductEntity.ts` — product boxes that animate between stations
5. Implement `WorkerOverlay.ts` — worker avatar, HR display, fatigue color
6. Build `SimulationPage.tsx` combining Canvas + controls
7. Build `SimControls.tsx` — play/pause/stop/speed buttons
8. Build `ParamPanel.tsx` — sliders for ConfigState params, "Apply" button sends PUT to `/api/config/update`
9. Wire `task_record` WebSocket events to Canvas state machine
10. **Keep Canvas rendering lightweight** — no heavy physics, simple geometric shapes, requestAnimationFrame

### Phase 4: Agent Chat Interface
**Goal**: Chat with the Cognitive Agent, see tool calls and reasoning trace.

1. Refactor `cognitive/agent.py`:
   - Add `system_prompt` constructor parameter (default: current hardcoded string)
   - Add `model_name` constructor parameter
   - Add `temperature` constructor parameter
   - Add `set_message_callback(callback)` method
   - Call callback during `monitor_cycle` for each thinking step, tool call, tool result, and final response
2. Implement `meta/routers/agent.py` — chat endpoint, trace endpoint, tools listing
3. Implement `/ws/agent/{sim_id}` WebSocket channel
4. Build `ChatPanel.tsx`, `MessageBubble.tsx`, `ToolCallCard.tsx`
5. Build `PromptButtons.tsx` with pre-built prompts (loaded from shortcuts in DB)
6. Build `TraceTimeline.tsx`
7. Build `AgentPage.tsx` combining chat + trace panels
8. Persist agent traces to SQLite

### Phase 5: Lean Knowledge Graph Visualization
**Goal**: Interactive D3.js force-directed graph, editable from dashboard.

1. Refactor `cognitive/lean_kg.py`:
   - Add methods: `add_node()`, `update_node()`, `delete_node()`, `add_edge()`, `delete_edge()`
   - Load overrides from SQLite if available, merge with JSON defaults
   - Add `export_graph()` and `import_graph()` methods
2. Implement `meta/routers/lean.py` — all endpoints from Section 5.2
3. Build `KnowledgeGraph.tsx` using D3.js force simulation
4. Build `MethodDetail.tsx` — slide-out detail panel
5. Build `GraphControls.tsx` — search, filter, zoom controls
6. Build `AnalysisShortcuts.tsx` — Muri, Bottleneck, Ergonomic buttons
7. Build `LeanPage.tsx`
8. Implement KG query endpoint that highlights triggered methods based on current KPIs

### Phase 6: Settings, Outputs & Polish
**Goal**: Full settings page, file browser, production-ready polish.

1. Build all Settings sub-pages:
   - `GeneralSettings.tsx` — output dir, defaults, host/port
   - `BrandingSettings.tsx` — title, subtitle, logo, accent color, theme
   - `LlmSettings.tsx` — API key, model, temperature (Google only)
   - `AgentSettings.tsx` — system prompt textarea, cycle interval, max tools
   - `DistributionEditor.tsx` — editable timing params table
   - `WorkerProfileEditor.tsx` — physio baselines editor
   - `LeanKgEditor.tsx` — CRUD for KG nodes/edges, import/export
   - `ShortcutManager.tsx` — prompt templates, analysis presets
2. Implement `meta/routers/outputs.py` — file listing, download, delete
3. Implement `meta/routers/shortcuts.py` — CRUD for shortcuts (SQLite-backed)
4. Build `FileBrowser.tsx`, `FilePreview.tsx`, `ComparisonView.tsx`
5. Build `OutputsPage.tsx`, `SettingsPage.tsx`
6. Add loading states, error boundaries, empty states to all pages
7. Build production bundle: `cd frontend && npm run build`, output to `meta/static/`
8. Verify: `python -m magi --web` serves the production build and everything works

---

## DESIGN CONSTRAINTS

### UI Rules
- **Light mode default**. All screenshots/first impressions must look good in light mode.
- **Professional and clean**. Think Google Cloud Console or Vercel Dashboard — not a gaming UI.
- **No unnecessary dependencies**. Every npm package must be justified.
- **Fast rendering**. Use `React.memo`, `useMemo`, `useCallback` where appropriate. Canvas visualization must maintain 30+ FPS.
- **Responsive sidebar**. Collapsible to icons on narrow screens.

### CSS Rules
- ALL colors via CSS custom properties (never hardcode `#hex` or `rgb()` in components)
- Theme switching via `[data-theme="dark"]` selector on `<html>`
- Font: Inter for UI, JetBrains Mono for code/data
- Border-radius: 8px for cards, 6px for inputs, 4px for badges
- Transitions: 150ms ease-out (keep it snappy)

### Backend Rules
- All API responses use Pydantic models (auto-validated, auto-documented)
- WebSocket messages are JSON with `{"type": "...", "data": {...}}` envelope
- SQLite DB file lives at `magi_data/magi.db` (created on first run)
- Thread safety: SimPy runs in threads, use `asyncio.run_coroutine_threadsafe` for bridge
- CORS: Allow all origins (configurable for production)
- Static files: Serve `meta/static/` at `/` for production SPA

### Existing Code Rules
- NEVER delete existing comments or docstrings
- NEVER change function signatures in ways that break existing callers
- All new parameters must have defaults (backward compatible)
- `cli.py` must not import anything from `meta/` (keep separation)
- Preserve all existing test paths (if any)

---

## VERIFICATION CHECKLIST

Before declaring any phase complete, verify:

- [ ] `python -m magi` runs the CLI experiment exactly as before
- [ ] `python -m magi --web` launches the dashboard and opens browser
- [ ] Light mode looks professional (not washed out, good contrast)
- [ ] Dark mode toggle works correctly
- [ ] No console errors in browser DevTools
- [ ] No Python tracebacks in server terminal
- [ ] WebSocket connections establish and stream data
- [ ] SQLite database is created and persists data across restarts
- [ ] Settings changes are persisted and applied on reload
- [ ] Simulation can be started, paused, resumed, stopped from the UI
- [ ] KPI charts update in real-time during simulation
- [ ] 2D Canvas visualization animates smoothly (30+ FPS)
- [ ] Agent chat sends messages and receives responses
- [ ] Lean KG graph renders and is interactive
- [ ] File browser lists output files correctly
- [ ] All settings are configurable from the Settings page
- [ ] Production build (`npm run build`) works and is served by FastAPI

---

## FILE REFERENCE

The complete codebase structure is documented in `implementation.md` Section 8.
All API endpoints are documented in `implementation.md` Section 5.2.
All WebSocket event schemas are documented in `implementation.md` Section 5.3.
All configurable parameters are documented in `implementation.md` Section 10.
All refactoring requirements are documented in `implementation.md` Section 11.
