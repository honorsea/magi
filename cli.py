"""
=============================================================================
  MAGI FRAMEWORK
  Silverline Assembly Line — Discrete Event Simulation
=============================================================================

  Project      : MAGI (Manufacturing Agentive Generative Intelligence) Framework
  Dataset      : AI-PRISM Silverline Assembly Line (Amasya, Turkey)
                 - Dataset 1: Worker Operation Durations (Lago Alvarez et al.,
                   Open Research Europe, 2025, DOI: 10.12688/openreseurope.20530.1)
                 - Dataset 2: Worker Physiological Signals (Toichoa Eyam, 2025,
                   DOI: 10.5281/zenodo.17658957)
  Description  : This module implements the Digital Twin (DT) layer of the
                 MAGI framework. It provides a high-fidelity Discrete Event
                 Simulation (DES) of the Silverline semi-automated assembly
                 line using SimPy. The simulation is driven entirely by
                 empirically-fitted probability distributions derived from
                 the preprocessing pipeline (1_data_preprocessing.py) and
                 empirical physiological baseline profiles extracted from the
                 EDA pipeline (2_physiological_eda.py).

  Architecture : This is LAYER 3 of the MAGI four-layer stack:
                 ┌─────────────────────────────────────────┐
                 │  Layer 4 – Cognitive (AI Agent / LLM)   │
                 ├─────────────────────────────────────────┤
                 │  Layer 3 – Digital Twin  ← THIS FILE    │
                 ├─────────────────────────────────────────┤
                 │  Layer 2 – Edge (Fatigue ML Classifier) │
                 ├─────────────────────────────────────────┤
                 │  Layer 1 – Physical (Physio Simulator)  │
                 └─────────────────────────────────────────┘

  Modularity   : The DT exposes a clean Tool API (Section 9) designed for
                 direct invocation by the Cognitive Layer (Layer 4). All
                 simulation parameters are encapsulated in a thread-safe
                 ConfigState object and can be modified at runtime without
                 restarting the simulation engine.

  Usage        :
    # Run a single baseline scenario (no AI intervention):
    dt = DigitalTwin()
    result = dt.run(duration_hours=8.0, seed=42)
    print(result.summary())

    # Use the Tool API (as the Cognitive Layer would):
    api = ToolAPI(dt)
    api.set_robot_speed_factor(1.15)
    api.assign_workers(cw_worker_id="002", mw_worker_id="001")
    kpis = api.get_current_kpis()

  Dependencies : simpy, numpy, scipy, pandas
  Python       : >= 3.9

=============================================================================
"""


import os
import sys
from pathlib import Path

# Add the parent directory to sys.path so 'from magi...' imports work
# when running from inside the magi directory itself.
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

import json
import time
import queue
import threading
import argparse
import traceback
from typing import Dict, Any, Optional

from magi.digital.config import ConfigState
from magi.digital.twin import DigitalTwin
from magi.digital.tool_api import ToolAPI
from magi.digital.replication import ReplicationRunner
from magi.digital.models import SimulationResult
from magi.cognitive.lean_kg import LeanKGRetriever
from magi.cognitive.sandbox import CodeSandbox
from magi.cognitive.agent import CognitiveAgent, HAS_GENAI
from magi.edge.fatigue import FatigueMonitor

# Force UTF-8 output on Windows consoles to avoid UnicodeEncodeError
import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # Fallback: some environments don't support reconfigure


#  SECTION 16 — MAIN ENTRY POINT (Experiment Runner)
#              Orchestrates: Baseline → MAGI → Statistical Comparison
# ─────────────────────────────────────────────────────────────────────────────

def _print_banner(text: str) -> None:
    w = 70
    print("\n" + "=" * w)
    print(f"  {text}")
    print("=" * w)


def _run_magi_simulation(
    dt:            DigitalTwin,
    api:           'ToolAPI',
    agent:         CognitiveAgent,
    duration_hours: float,
    seed:          int,
    speed_factor:  float,
) -> SimulationResult:
    """
    Run the MAGI-enhanced simulation with the Cognitive Agent active.
    The simulation runs in a background thread while the main thread
    handles user CLI input.
    """
    dt.config.update(simulation_speed_factor=speed_factor)

    # Thread-safe message queue for user → agent communication
    msg_queue: queue.Queue = queue.Queue()

    # Agent callback state
    last_poll = [0.0]
    poll_interval = agent.POLL_INTERVAL_SIM_S

    def agent_callback(env, task_log, physio_log):
        """Called after every SimPy event during real-time mode."""
        has_msgs = not msg_queue.empty()
        enough_time = (env.now - last_poll[0]) >= poll_interval

        if enough_time or has_msgs:
            last_poll[0] = env.now
            user_msgs = []
            while not msg_queue.empty():
                try:
                    user_msgs.append(msg_queue.get_nowait())
                except queue.Empty:
                    break
            # Run agent monitoring cycle
            agent.monitor_cycle(env, task_log, physio_log, user_messages=user_msgs)

    # Run simulation in background thread
    sim_result_holder = [None]
    sim_error_holder = [None]

    def sim_thread_fn():
        try:
            result = dt.run(
                duration_hours=duration_hours,
                seed=seed,
                realtime=True,
                step_callback=agent_callback,
            )
            sim_result_holder[0] = result
        except Exception as e:
            sim_error_holder[0] = e
            traceback.print_exc()

    sim_thread = threading.Thread(target=sim_thread_fn, daemon=True)
    sim_thread.start()

    # ── CLI input loop (main thread) ──────────────────────────────────
    print("\n  +------------------------------------------------------+")
    print("  |  MAGI Simulation Running -- Interactive CLI Active   |")
    print("  |  Commands: status, speed <N>, pause, resume,        |")
    print("  |            help, quit                                |")
    print("  |  Or type any message to talk to the AI agent.       |")
    print("  +------------------------------------------------------+\n")

    while sim_thread.is_alive():
        try:
            user_input = None
            # Non-blocking-ish input with timeout
            import sys
            import select
            if sys.platform == "win32":
                # Windows: use a polling approach
                import msvcrt
                line_buf = []
                while sim_thread.is_alive():
                    if msvcrt.kbhit():
                        ch = msvcrt.getwch()
                        if ch == '\r' or ch == '\n':
                            user_input = "".join(line_buf)
                            line_buf.clear()
                            print()  # newline after input
                            break
                        elif ch == '\x08':  # backspace
                            if line_buf:
                                line_buf.pop()
                                sys.stdout.write('\b \b')
                                sys.stdout.flush()
                        else:
                            line_buf.append(ch)
                            sys.stdout.write(ch)
                            sys.stdout.flush()
                    else:
                        time.sleep(0.1)
            else:
                # Unix: use select
                ready, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ready:
                    user_input = sys.stdin.readline().strip()

            if user_input is None:
                continue
            if not user_input:
                continue

            cmd = user_input.strip().lower()

            if cmd in ("quit", "exit", "q"):
                print("  [CLI] Stopping simulation...")
                # Force simulation end by advancing time
                dt.config.update(simulation_speed_factor=999999.0)
                break
            elif cmd == "help":
                print("  Commands: status, speed <N>, pause, resume, quit, help")
                print("  Anything else is sent as a message to the AI agent.")
            elif cmd == "status":
                cfg = dt.config.snapshot()
                sim_spd = cfg.get("simulation_speed_factor", 1.0)
                print(f"  [Status] Speed={sim_spd}x, Config={cfg}")
            elif cmd.startswith("speed "):
                try:
                    new_speed = float(cmd.split()[1])
                    dt.config.update(simulation_speed_factor=new_speed)
                    print(f"  [CLI] Speed set to {new_speed}x")
                except (ValueError, IndexError):
                    print("  [CLI] Usage: speed <number>")
            elif cmd == "pause":
                dt.config.update(simulation_speed_factor=0.001)
                print("  [CLI] Simulation paused (speed -> 0.001x)")
            elif cmd == "resume":
                dt.config.update(simulation_speed_factor=speed_factor)
                print(f"  [CLI] Simulation resumed (speed -> {speed_factor}x)")
            else:
                # Send to agent
                msg_queue.put(user_input)
                print(f"  [CLI] Message queued for agent: '{user_input[:80]}'")

        except (EOFError, KeyboardInterrupt):
            print("\n  [CLI] Interrupted. Stopping simulation...")
            dt.config.update(simulation_speed_factor=999999.0)
            break

    sim_thread.join(timeout=30)

    if sim_error_holder[0]:
        raise sim_error_holder[0]

    return sim_result_holder[0]


# ─────────────────────────────────────────────────────────────────────────────

def main():
    """
    MAGI Framework — Complete Experiment Runner.

    Phases:
    1. BASELINE: Run simulation without AI agent (accelerated, 30 replications)
    2. MAGI: Run simulation with Cognitive Agent active (real-time, interactive)
    3. COMPARISON: Statistical comparison of baseline vs MAGI's final config
    4. REPORT: Print results and save all outputs
    """

    # ── Parse arguments ───────────────────────────────────────────────
    parser = argparse.ArgumentParser(description="MAGI Framework Experiment")
    parser.add_argument("--speed", type=float, default=120.0,
                        help="Simulation speed factor for MAGI run (default: 120)")
    parser.add_argument("--duration", type=float, default=8.0,
                        help="Simulated shift duration in hours (default: 8)")
    parser.add_argument("--replications", type=int, default=30,
                        help="Number of replications for statistical comparison (default: 30)")
    parser.add_argument("--seed", type=int, default=1000,
                        help="Base random seed (default: 1000)")
    parser.add_argument("--model", type=str, default="gemma-4-31b-it",
                        help="LLM model name (default: gemma-4-31b-it)")
    parser.add_argument("--skip-magi", action="store_true",
                        help="Skip the MAGI run (baseline only)")
    parser.add_argument("--output-dir", type=str, default="./magi_outputs",
                        help="Output directory (default: ./magi_outputs)")
    args = parser.parse_args()

    OUTPUT_DIR = args.output_dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    _print_banner("MAGI FRAMEWORK — MANUFACTURING AGENTIVE GENERATIVE INTELLIGENCE")
    print(f"  Duration     : {args.duration}h")
    print(f"  Replications : {args.replications}")
    print(f"  Base seed    : {args.seed}")
    print(f"  MAGI speed   : {args.speed}x")
    print(f"  Model        : {args.model}")
    print(f"  Output dir   : {OUTPUT_DIR}")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 1 — BASELINE (Mode A: No AI Intervention)
    # ══════════════════════════════════════════════════════════════════
    _print_banner("PHASE 1 — BASELINE RUN (No AI Agent)")

    dt_baseline = DigitalTwin(ConfigState(
        cw_worker_id="001", mw_worker_id="001",
        robot_speed_factor=1.0, takt_time_seconds=60.0,
    ))
    result_baseline = dt_baseline.run(duration_hours=args.duration, seed=args.seed)
    print(result_baseline.summary())

    baseline_kpis = result_baseline.kpis

    df_baseline = result_baseline.to_dataframe()
    df_baseline.to_csv(os.path.join(OUTPUT_DIR, "baseline_task_log.csv"), index=False)
    print(f"  -> Baseline task log saved ({len(df_baseline)} rows)")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 2 — MAGI RUN (Mode B: AI Agent Active)
    # ══════════════════════════════════════════════════════════════════
    result_magi = None
    agent = None

    if not args.skip_magi:
        _print_banner("PHASE 2 — MAGI RUN (AI Agent Active)")

        if not HAS_GENAI:
            print("  ERROR: google-genai SDK not installed.")
            print("  Install with: pip install google-genai")
            print("  Skipping MAGI run.")
        elif not os.environ.get("GOOGLE_API_KEY"):
            print("  ERROR: GOOGLE_API_KEY not set.")
            print("  Create a .env file with: GOOGLE_API_KEY=your_key_here")
            print("  Skipping MAGI run.")
        else:
            # Fresh DT with same baseline config
            dt_magi = DigitalTwin(ConfigState(
                cw_worker_id="001", mw_worker_id="001",
                robot_speed_factor=1.0, takt_time_seconds=60.0,
                simulation_speed_factor=args.speed,
            ))
            api_magi = ToolAPI(dt_magi)

            # Initialise Cognitive Layer components
            lean_kg   = LeanKGRetriever("./lean_kg_output")
            sandbox   = CodeSandbox(OUTPUT_DIR)
            fat_mon   = FatigueMonitor()

            agent = CognitiveAgent(
                tool_api=api_magi,
                lean_kg=lean_kg,
                sandbox=sandbox,
                fatigue_monitor=fat_mon,
                model_name=args.model,
                output_dir=OUTPUT_DIR,
            )
            agent.set_baseline_kpis(baseline_kpis)

            # Run interactive MAGI simulation
            try:
                result_magi = _run_magi_simulation(
                    dt=dt_magi, api=api_magi, agent=agent,
                    duration_hours=args.duration, seed=args.seed,
                    speed_factor=args.speed,
                )
            except Exception as e:
                print(f"  MAGI run error: {e}")
                traceback.print_exc()

            if result_magi:
                print(result_magi.summary())
                df_magi = result_magi.to_dataframe()
                df_magi.to_csv(os.path.join(OUTPUT_DIR, "magi_task_log.csv"), index=False)
                print(f"  -> MAGI task log saved ({len(df_magi)} rows)")

                # Save agent trace
                agent.save_trace(os.path.join(OUTPUT_DIR, "agent_trace.json"))
                agent.print_trace_summary()

                # Save final config
                final_config = api_magi.get_config_snapshot()
                with open(os.path.join(OUTPUT_DIR, "magi_final_config.json"), "w") as f:
                    json.dump(final_config, f, indent=2)
                print(f"  -> Final MAGI config: {final_config}")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 3 — STATISTICAL COMPARISON (Paired Replications)
    # ══════════════════════════════════════════════════════════════════
    _print_banner(f"PHASE 3 — STATISTICAL COMPARISON ({args.replications} Replications)")

    # Baseline replications (default config)
    dt_rep_base = DigitalTwin(ConfigState(
        cw_worker_id="001", mw_worker_id="001",
        robot_speed_factor=1.0, takt_time_seconds=60.0,
    ))
    runner_base = ReplicationRunner(dt_rep_base)
    df_rep_base = runner_base.run_replications(
        n=args.replications, duration_hours=args.duration,
        base_seed=args.seed, label="baseline",
    )

    # MAGI replications (using MAGI's final config if available)
    if result_magi:
        # Use whatever config the agent settled on
        magi_config = ConfigState(**{
            k: v for k, v in api_magi.get_config_snapshot().items()
            if not k.startswith("simulation")
        })
        # Keep simulation_speed_factor at default for accelerated replications
        dt_rep_magi = DigitalTwin(magi_config)
    else:
        # Fallback: same as baseline (comparison will show no difference)
        dt_rep_magi = DigitalTwin(ConfigState(
            cw_worker_id="001", mw_worker_id="001",
            robot_speed_factor=1.0, takt_time_seconds=60.0,
        ))

    runner_magi = ReplicationRunner(dt_rep_magi)
    df_rep_magi = runner_magi.run_replications(
        n=args.replications, duration_hours=args.duration,
        base_seed=args.seed, label="magi",
    )

    # Paired comparison
    comparison_df = ReplicationRunner.compute_paired_comparison(df_rep_base, df_rep_magi)

    _print_banner("PAIRED t-TEST RESULTS")
    print(comparison_df.to_string(index=False))

    # Save all outputs
    df_rep_base.to_csv(os.path.join(OUTPUT_DIR, "replications_baseline.csv"), index=False)
    df_rep_magi.to_csv(os.path.join(OUTPUT_DIR, "replications_magi.csv"), index=False)
    comparison_df.to_csv(os.path.join(OUTPUT_DIR, "kpi_comparison.csv"), index=False)

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 4 — FINAL REPORT
    # ══════════════════════════════════════════════════════════════════
    _print_banner("EXPERIMENT COMPLETE")

    print(f"\n  Output files in '{OUTPUT_DIR}/':")
    for fn in sorted(os.listdir(OUTPUT_DIR)):
        fp = os.path.join(OUTPUT_DIR, fn)
        if os.path.isfile(fp):
            size_kb = os.path.getsize(fp) / 1024
            print(f"    {fn:40s}  {size_kb:8.1f} KB")

    if agent:
        print(f"\n  Agent monitoring cycles: {len(agent.get_trace())}")
        print(f"  Agent tool calls: {sum(len(t.tool_calls) for t in agent.get_trace())}")
        files = [f for t in agent.get_trace() for f in t.files_created]
        if files:
            print(f"  Agent-generated files: {len(files)}")
            for f in files:
                print(f"    -> {f}")

    print(f"\n  {'=' * 70}")
    print("  MAGI Framework experiment completed successfully.")
    print(f"  {'=' * 70}")

