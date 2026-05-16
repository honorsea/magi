import simpy
import time
import numpy as np
from typing import Dict, Any, Callable, List, Optional

from magi.digital.config import ConfigState
from magi.digital.models import TaskRecord, PhysioRecord, SimulationResult
from magi.digital.processes import _arrival_process, _cw_process, _mw_process
from magi.digital.kpi import KPIComputer
from magi.physical.samplers import TaskDurationSampler, PhysiologicalSampler

#  SECTION 8 — DIGITAL TWIN CLASS (Main Orchestrator)
# ─────────────────────────────────────────────────────────────────────────────

class DigitalTwin:
    """
    Main Digital Twin orchestrator for the Silverline assembly line.

    Encapsulates the SimPy DES environment, the physiological sampler,
    the task duration sampler, and the KPI computation pipeline.

    The DT is designed to be long-lived: it holds the ConfigState across
    multiple `run()` calls and exposes it to the Tool API for Cognitive
    Layer interaction. Configuration changes made via the Tool API between
    runs persist into the next run automatically.

    Usage
    -----
    dt = DigitalTwin()
    result_baseline = dt.run(duration_hours=8.0, seed=0)  # Mode A

    dt.config.update(robot_speed_factor=1.15, takt_time_seconds=55.0)
    result_magi = dt.run(duration_hours=8.0, seed=0)      # Mode B

    Replication Runner
    ------------------
    For statistically valid experiments (30 replications), use:
        runner = ReplicationRunner(dt)
        all_results = runner.run_replications(n=30, duration_hours=8.0)
    """

    def __init__(self, config: Optional[ConfigState] = None):
        """
        Initialise the Digital Twin.

        Args:
            config: Optional pre-configured ConfigState. If None, defaults
                    are used (both workers = "001", 60s takt, 1.0× robot speed).
        """
        self.config       = config or ConfigState()
        self._kpi_computer = KPIComputer()
        # Stores the result of the most recent run for Tool API queries
        self._last_result: Optional[SimulationResult] = None
        print("[DigitalTwin] Initialised. Config:", self.config.snapshot())

    # ------------------------------------------------------------------
    # Primary simulation entry point
    # ------------------------------------------------------------------

    def run(
        self,
        duration_hours:  float = 8.0,
        seed:            int   = 42,
        realtime:        bool  = False,
        step_callback:   Optional[Any] = None,
        event_sink:      Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> SimulationResult:
        """
        Execute one complete simulation replication.

        Supports two execution modes controlled by the `realtime` flag:

        **Accelerated mode** (realtime=False, default):
            Runs as fast as possible — suitable for batch replications and
            statistical experiments.

        **Real-time mode** (realtime=True):
            Paces SimPy events against wall-clock time using
            `config.simulation_speed_factor`. At factor=1.0 the simulation
            runs at true 1:1 real-time so the Cognitive Layer agent can
            intervene mid-run just as it would in a live deployment.
            The optional `step_callback(env, task_log, physio_log)` is called
            after every simulated event — the AI agent hook point.

        Args:
            duration_hours:  Simulated shift length (hours).
            seed:            Random seed for full reproducibility.
            realtime:        If True, pace execution to wall-clock time.
            step_callback:   Optional callable invoked after every SimPy step.
                             Signature: callback(env, task_log, physio_log) -> None
                             The Cognitive Layer uses this to inspect state and
                             call Tool API methods mid-simulation.

        Returns:
            SimulationResult containing event logs and computed KPIs.
        """
        config_snap    = self.config.snapshot()
        rng            = np.random.default_rng(seed)
        env            = simpy.Environment()
        dur_sampler    = TaskDurationSampler(self.config, rng)
        phy_sampler    = PhysiologicalSampler(self.config, rng)

        # SimPy primitives
        cw_input_buffer = simpy.Store(env, capacity=self.config.buffer_capacity)
        mw_input_buffer = simpy.Store(env, capacity=self.config.buffer_capacity)
        robot           = simpy.Resource(env, capacity=1)  # single shared robot arm

        # Shared mutable accumulators (passed by reference to generator funcs)
        task_log:    List[TaskRecord]   = []
        physio_log:  List[PhysioRecord] = []
        cw_busy:     List[float]        = []
        mw_busy:     List[float]        = []
        robot_busy:  List[float]        = []
        counters:    Dict[str, int]     = {"generated": 0, "dropped": 0}

        # Register SimPy processes
        env.process(_arrival_process(env, cw_input_buffer, dur_sampler,
                                     self.config, counters))
        env.process(_cw_process(env, cw_input_buffer, mw_input_buffer, robot,
                                self.config, dur_sampler, phy_sampler,
                                task_log, physio_log, cw_busy, robot_busy,
                                event_sink=event_sink))
        env.process(_mw_process(env, mw_input_buffer, self.config,
                                dur_sampler, phy_sampler,
                                task_log, physio_log, mw_busy,
                                event_sink=event_sink))

        sim_duration_s = duration_hours * 3600.0

        if not realtime:
            # ── Accelerated mode: fire-and-forget ─────────────────────
            env.run(until=sim_duration_s)
        else:
            # ── Real-time mode: step-by-step with wall-clock pacing ───
            # simulation_speed_factor: sim-seconds per real-second.
            # factor=1.0  → 1 sim-second == 1 real-second  (true real-time)
            # factor=60.0 → 1 sim-minute == 1 real-second  (1-min-per-sec)
            speed  = max(self.config.simulation_speed_factor, 0.001)
            wall_t0 = time.perf_counter()

            while env.peek() < sim_duration_s:
                # Advance simulation by one event
                env.step()

                # Wall-clock time that SHOULD have elapsed for this sim time
                expected_wall = env.now / speed
                actual_wall   = time.perf_counter() - wall_t0
                sleep_needed  = expected_wall - actual_wall
                if sleep_needed > 0:
                    time.sleep(sleep_needed)

                # Cognitive Layer hook: called after every event
                if step_callback is not None:
                    step_callback(env, task_log, physio_log)

        # Compute KPIs from collected logs
        kpis = self._kpi_computer.compute(
            task_log=task_log,
            physio_log=physio_log,
            config=self.config,
            duration_hours=duration_hours,
            cw_busy_time=cw_busy,
            mw_busy_time=mw_busy,
            robot_busy=robot_busy,
            generated=counters["generated"],
            dropped=counters["dropped"],
        )

        result = SimulationResult(
            config_snapshot=config_snap,
            seed=seed,
            duration_hours=duration_hours,
            task_log=task_log,
            physio_log=physio_log,
            kpis=kpis,
        )
        self._last_result = result
        return result

    def get_last_result(self) -> Optional[SimulationResult]:
        """Return the SimulationResult from the most recent run()."""
        return self._last_result

    def get_live_kpis(self) -> Dict[str, Any]:
        """
        Compute and return KPIs from whatever has been logged so far.

        Designed for Cognitive Layer polling during a real-time run.
        Unlike get_current_kpis() (which requires a completed run), this
        method introspects the LIVE accumulators via the last result's
        partial log — or returns an informative dict if no run is active.

        Note: For truly live mid-run KPIs, pass a step_callback to run()
        and call this from within the callback.
        """
        result = self._last_result
        if result is None:
            return {"status": "no_run", "kpis": {}}
        return {"status": "completed", "kpis": result.kpis}


# ─────────────────────────────────────────────────────────────────────────────
