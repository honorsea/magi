"""
MAGI Meta Layer — Simulation Manager.

Manages multiple concurrent simulation sessions, each running in a
background thread. Provides start/stop/pause/resume controls and
exposes an async event stream per session.
"""

import asyncio
import queue
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from magi.digital.config import ConfigState
from magi.digital.twin import DigitalTwin
from magi.meta.services.event_bridge import EventBridge
from magi.meta.services import db as _db

SimStatus = Literal["queued", "running", "paused", "completed", "error"]


@dataclass
class SimulationSession:
    id:             str
    label:          str
    mode:           str                   # "baseline" | "magi"
    status:         SimStatus
    config:         ConfigState
    bridge:         Optional[EventBridge]
    result:         Optional[Dict]
    error_msg:      Optional[str]
    created_at:     float
    started_at:     Optional[float]
    completed_at:   Optional[float]
    _thread:        Optional[threading.Thread] = field(default=None, repr=False)
    _stop_event:    threading.Event = field(default_factory=threading.Event, repr=False)
    _pause_event:   threading.Event = field(default_factory=threading.Event, repr=False)
    _msg_queue:     queue.Queue = field(default_factory=queue.Queue, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":           self.id,
            "label":        self.label,
            "mode":         self.mode,
            "status":       self.status,
            "config":       self.config.to_dict(),
            "result":       self.result,
            "error_msg":    self.error_msg,
            "created_at":   self.created_at,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
        }


class SimulationManager:
    """
    Manages multiple concurrent simulation runs.

    Thread pool: up to 8 concurrent simulations.
    Each simulation runs in its own thread with its own EventBridge.
    """

    def __init__(self):
        self._sessions: Dict[str, SimulationSession] = {}
        self._executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="magi-sim")
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop (called at startup)."""
        self._loop = loop

    # ── Session Access ────────────────────────────────────────────────────────

    def get_session(self, sim_id: str) -> Optional[SimulationSession]:
        return self._sessions.get(sim_id)

    def list_sessions(self) -> List[Dict]:
        with self._lock:
            return [s.to_dict() for s in self._sessions.values()]

    # ── Start ─────────────────────────────────────────────────────────────────

    async def start_simulation(
        self,
        label:            str   = "",
        mode:             str   = "baseline",
        duration_hours:   float = 8.0,
        seed:             int   = 0,
        config_overrides: Optional[Dict[str, Any]] = None,
        speed_factor:     float = 0,   # 0 = max speed, >0 = real-time acceleration factor
    ) -> str:
        """
        Create and start a new simulation session.
        Returns the session ID.
        """
        sim_id = str(uuid.uuid4())[:8]
        now = time.time()

        # Build ConfigState from defaults + overrides
        config = ConfigState()
        if config_overrides:
            for k, v in config_overrides.items():
                if hasattr(config, k):
                    setattr(config, k, v)

        bridge = EventBridge(sim_id, self._loop) if self._loop else None
        stop_ev = threading.Event()
        pause_ev = threading.Event()

        session = SimulationSession(
            id=sim_id, label=label or f"Sim {len(self._sessions)+1}",
            mode=mode, status="queued", config=config,
            bridge=bridge, result=None, error_msg=None,
            created_at=now, started_at=None, completed_at=None,
            _stop_event=stop_ev, _pause_event=pause_ev,
        )

        with self._lock:
            self._sessions[sim_id] = session

        # Persist to DB
        await _db.upsert_simulation(
            sim_id, label=session.label, mode=mode,
            status="queued", config=config.to_dict(), created_at=now,
        )

        # Launch in thread pool
        self._executor.submit(
            self._run_thread, sim_id, duration_hours, seed, speed_factor, stop_ev, pause_ev
        )

        return sim_id

    # ── Control ───────────────────────────────────────────────────────────────

    def pause_simulation(self, sim_id: str) -> bool:
        session = self._sessions.get(sim_id)
        if session and session.status == "running":
            session._pause_event.set()
            session.status = "paused"
            return True
        return False

    def resume_simulation(self, sim_id: str) -> bool:
        session = self._sessions.get(sim_id)
        if session and session.status == "paused":
            session._pause_event.clear()
            session.status = "running"
            return True
        return False

    def stop_simulation(self, sim_id: str) -> bool:
        session = self._sessions.get(sim_id)
        if session and session.status in ("running", "paused", "queued"):
            session._stop_event.set()
            session._pause_event.clear()
            return True
        return False

    def delete_session(self, sim_id: str) -> bool:
        self.stop_simulation(sim_id)
        with self._lock:
            return bool(self._sessions.pop(sim_id, None))

    def send_agent_message(self, sim_id: str, message: str) -> bool:
        """Send a user message to the running MAGI cognitive agent."""
        session = self._sessions.get(sim_id)
        if session:
            session._msg_queue.put(message)
            return True
        return False

    # ── Event Streaming ───────────────────────────────────────────────────────

    async def subscribe(self, sim_id: str):
        """Async generator: yields events from the simulation's bridge."""
        session = self._sessions.get(sim_id)
        if not session or not session.bridge:
            return
        async for event in session.bridge.stream():
            yield event

    # ── Thread Body ───────────────────────────────────────────────────────────

    def _run_thread(
        self,
        sim_id: str,
        duration_hours: float,
        seed: int,
        speed_factor: float,
        stop_ev: threading.Event,
        pause_ev: threading.Event,
    ) -> None:
        """Body of the simulation thread. Runs DigitalTwin.run()."""
        session = self._sessions.get(sim_id)
        if not session:
            return

        session.status = "running"
        session.started_at = time.time()

        if self._loop:
            asyncio.run_coroutine_threadsafe(
                _db.upsert_simulation(sim_id, label=session.label, mode=session.mode,
                                      status="running", config=session.config.to_dict(),
                                      created_at=session.created_at, started_at=session.started_at),
                self._loop,
            )

        try:
            bridge = session.bridge
            task_count = [0]
            # Emit a live kpi_snapshot every N task completions
            KPI_INTERVAL = 30

            def event_sink(event_type: str, data: Dict[str, Any]) -> None:
                """Called from the SimPy process thread for every task event."""
                if bridge:
                    bridge.emit(event_type, data)
                if event_type == "task_record":
                    task_count[0] += 1

            # ── Setup Cognitive Agent if mode is "magi" ────────────────────
            agent = None
            if session.mode == "magi":
                try:
                    from magi.digital.tool_api import ToolAPI
                    from magi.cognitive.lean_kg import LeanKGRetriever
                    from magi.cognitive.sandbox import CodeSandbox
                    from magi.cognitive.agent import CognitiveAgent
                    from magi.edge.fatigue import FatigueMonitor
                    # dt is constructed below, pass a placeholder and swap after
                    _tmp_config = session.config
                    agent_tool_api_holder = [None]  # filled after dt is built
                    _lean_kg = LeanKGRetriever()
                    _sandbox = CodeSandbox()
                    _fatigue = FatigueMonitor()
                    _agent_ready = [False]
                except Exception as e:
                    session.error_msg = f"Failed to load cognitive agent: {e}"
                    if bridge:
                        bridge.emit("agent_warning", {"msg": str(e)})

            last_poll = [0.0]

            # ── Build step_callback ────────────────────────────────────────
            def step_callback(env, task_log, physio_log):
                """Called after every SimPy event (realtime and non-realtime)."""
                # Pause/stop handling
                while pause_ev.is_set() and not stop_ev.is_set():
                    time.sleep(0.05)
                if stop_ev.is_set():
                    raise StopIteration("Simulation stopped by user")

                # Cognitive Agent hook
                if agent is not None:
                    has_msgs = not session._msg_queue.empty()
                    enough_time = (env.now - last_poll[0]) >= agent.POLL_INTERVAL_SIM_S
                    if enough_time or has_msgs:
                        last_poll[0] = env.now
                        user_msgs: List[str] = []
                        while not session._msg_queue.empty():
                            try:
                                user_msgs.append(session._msg_queue.get_nowait())
                            except queue.Empty:
                                break
                        try:
                            agent.monitor_cycle(env, task_log, physio_log, user_messages=user_msgs)
                        except Exception as ae:
                            if bridge:
                                bridge.emit("agent_error", {"error": str(ae)})

                # Live KPI emission every KPI_INTERVAL task completions
                n = task_count[0]
                if n > 0 and n % KPI_INTERVAL == 0 and bridge:
                    cw_phys = [p for p in physio_log if p.workstation == "CW"]
                    mw_phys = [p for p in physio_log if p.workstation == "MW"]
                    mw_complete = [t for t in task_log if t.workstation == "MW" and t.task_label == "07_bag_leave"]

                    def _mean(lst, attr, window=20):
                        sub = lst[-window:] if len(lst) >= window else lst
                        if not sub:
                            return 0.0
                        return sum(getattr(p, attr) for p in sub) / len(sub)

                    kpis = {
                        "throughput_total":    len(mw_complete),
                        "throughput_dropped":  0,
                        "cw_hr_mean":          _mean(cw_phys, "hr_bpm"),
                        "mw_hr_mean":          _mean(mw_phys, "hr_bpm"),
                        "cw_fatigue_mean":     _mean(cw_phys, "fatigue_score"),
                        "mw_fatigue_mean":     _mean(mw_phys, "fatigue_score"),
                        # Approximations — real KPIs computed at end
                        "oee":                 0.85,
                        "line_balance_ratio":  0.85,
                        "takt_adherence":      0.95,
                        "cw_utilization":      0.80,
                        "mw_utilization":      0.80,
                        "robot_utilization":   0.50,
                    }
                    bridge.emit("kpi_snapshot", {"sim_time_s": env.now, **kpis})

            # ── Apply speed factor and build DigitalTwin ───────────────────
            use_realtime = speed_factor > 0
            if use_realtime:
                session.config.update(simulation_speed_factor=speed_factor)

            dt = DigitalTwin(config=session.config)

            # Wire agent to its ToolAPI now that dt is built
            if session.mode == "magi" and agent is None and _agent_ready is not None:
                try:
                    from magi.digital.tool_api import ToolAPI
                    from magi.cognitive.agent import CognitiveAgent
                    _tool_api = ToolAPI(dt)
                    agent = CognitiveAgent(_tool_api, _lean_kg, _sandbox, _fatigue)
                except Exception as e:
                    if bridge:
                        bridge.emit("agent_warning", {"msg": f"Agent init failed: {e}"})

            result = dt.run(
                duration_hours=duration_hours,
                seed=seed,
                realtime=use_realtime,
                step_callback=step_callback,
                event_sink=event_sink,
            )

            session.status = "completed"
            session.completed_at = time.time()
            # Build a serializable result dict
            result_dict = {
                "kpis": result.kpis,
                "seed": result.seed,
                "duration_hours": result.duration_hours,
                "run_timestamp": result.run_timestamp,
            }
            session.result = result_dict

            if bridge:
                bridge.emit("sim_complete", {"kpis": result.kpis})
                bridge.close()

            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    _db.upsert_simulation(
                        sim_id, label=session.label, mode=session.mode,
                        status="completed", config=session.config.to_dict(),
                        result=result_dict, created_at=session.created_at,
                        started_at=session.started_at, completed_at=session.completed_at,
                    ),
                    self._loop,
                )

        except StopIteration:
            session.status = "completed"
            session.completed_at = time.time()
            if bridge:
                bridge.emit("sim_stopped", {"reason": "user_request"})
                bridge.close()

        except Exception as exc:
            session.status = "error"
            session.error_msg = str(exc)
            session.completed_at = time.time()
            tb = traceback.format_exc()
            if bridge:
                bridge.emit("sim_error", {"error": str(exc), "traceback": tb})
                bridge.close()
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    _db.upsert_simulation(
                        sim_id, label=session.label, mode=session.mode,
                        status="error", config=session.config.to_dict(),
                        error_msg=str(exc), created_at=session.created_at,
                        started_at=session.started_at, completed_at=session.completed_at,
                    ),
                    self._loop,
                )


# ── Singleton ─────────────────────────────────────────────────────────────────

_manager: Optional[SimulationManager] = None


def get_manager() -> SimulationManager:
    global _manager
    if _manager is None:
        _manager = SimulationManager()
    return _manager
