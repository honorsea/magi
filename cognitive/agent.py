import os
import json
import time
import textwrap
import traceback
import queue
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from collections import defaultdict

try:
    from google import genai
    from google.genai import types as genai_types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from magi.physical.constants import PHYSIO_CTRL_HR
from magi.digital.config import ConfigState
from magi.digital.models import PhysioRecord, TaskRecord
from magi.digital.tool_api import ToolAPI
from magi.cognitive.lean_kg import LeanKGRetriever
from magi.cognitive.sandbox import CodeSandbox
from magi.edge.fatigue import FatigueMonitor

#  SECTION 15 — COGNITIVE AGENT (Layer 4 — LLM Core)
#              Google Gemini-based agent with tool calling, RAG, and
#              code execution for autonomous production line optimisation.
# ─────────────────────────────────────────────────────────────────────────────

_MAGI_SYSTEM_PROMPT = textwrap.dedent("""\
You are the MAGI Cognitive Agent — an AI manufacturing engineer operating
the Silverline assembly line digital twin. You are Layer 4 of the MAGI
(Manufacturing Agentive Generative Intelligence) framework, an Industry 5.0
smart manufacturing system.

## Your Responsibilities
1. MONITOR: Continuously surveil production KPIs and physiological signals.
2. DETECT: Identify deviations, bottlenecks, fatigue, and waste.
3. REASON: Apply Lean manufacturing methodologies from your knowledge base
   to diagnose root causes and propose countermeasures.
4. ACT: Implement parameter changes via the Tool API.
5. VERIFY: Check that interventions had the intended effect.
6. PROTECT: Prioritise operator wellbeing (Industry 5.0 human-centricity).

## Your Knowledge Base
You have access to a Lean Manufacturing Knowledge Graph containing methods
including: {method_list}

Use retrieve_lean_methods to find applicable methods for the current
situation, and get_lean_method_detail for full methodology information.

## Decision Framework
Follow the PDCA (Plan-Do-Check-Act) cycle for every intervention:
- PLAN: Analyse KPIs, query knowledge graph, reason about root cause.
- DO: Apply parameter change via Tool API.
- CHECK: Wait for next monitoring cycle, compare KPIs.
- ACT: Standardise if improved, revert if not.

## Operator Wellbeing (CRITICAL — Industry 5.0 Human-Centricity)
- fatigue_score >= 0.6 → WARNING: Consider takt time increase or worker swap.
- fatigue_score >= 0.8 → CRITICAL: Immediate intervention required.
- HR sustained >12% above CTRL baseline → Cardiovascular overload.
- Always weigh throughput gains against ergonomic costs.
- You may slow down production, swap workers, or adjust robot speed to
  protect operators. Operator safety always takes precedence.

## Code Execution
You can write and execute Python code for:
- OR-Tools mathematical optimisation (linear programming, CP-SAT)
- matplotlib visualisations (Ishikawa diagrams, VSM maps, time-series plots)
- Statistical analysis and what-if scenario computations
- Any other analytical computation

When creating plots, save them to the _OUTPUT_DIR variable (pre-defined).
Use descriptive filenames. The user will see any files you create.

## Simulation Parameters You Can Control
- robot_speed_factor: [0.5, 2.0] — Robot arm speed multiplier
- takt_time_seconds: [20, 300] — Product arrival interval
- buffer_capacity: [1, 20] — Inter-station WIP buffer size
- worker_assignment: CW and MW workers from {{001, 002, 003, 004}}
- simulation_speed: Runtime speed of the simulation itself

## Worker Physiological Profiles (CTRL baselines)
- Worker 001: CTRL HR = 81.93 BPM (lowest — best for high-demand station)
- Worker 002: CTRL HR = 81.23 BPM
- Worker 003: CTRL HR = 83.54 BPM (highest baseline — most fatigue-prone)
- Worker 004: CTRL HR = 82.16 BPM

## Constraints
- You operate within a SIMULATED environment.
- DO NOT fabricate data or metrics — only use what the tools provide.
- Be creative and proactive. Monitor, reason, and act autonomously.
- When the user asks you something, respond helpfully and use your tools.
- Log your reasoning so it can be reviewed after the simulation.
""")


@dataclass
class AgentTraceEntry:
    """One entry in the agent's reasoning trace (for post-run review)."""
    sim_time_s:    float
    wall_time:     str
    trigger:       str     # "auto_monitor" | "user_message" | "fatigue_alert"
    state_summary: Dict[str, Any]
    user_message:  Optional[str]
    agent_text:    str
    tool_calls:    List[Dict[str, Any]]
    tool_results:  List[Dict[str, Any]]
    files_created: List[str]


class CognitiveAgent:
    """
    LLM-based Cognitive Agent (Layer 4) for the MAGI framework.

    Uses Google GenAI SDK with tool calling to monitor, reason about,
    and optimise the digital twin in real time. Maintains full conversation
    history and an intervention trace for post-run analysis.
    """

    POLL_INTERVAL_SIM_S = 30 * 60   # 30 simulated minutes between polls
    MIN_COOLDOWN_S      = 5 * 60    # Minimum 5 sim-minutes between interventions

    def __init__(
        self,
        tool_api:        'ToolAPI',
        lean_kg:         LeanKGRetriever,
        sandbox:         CodeSandbox,
        fatigue_monitor: FatigueMonitor,
        model_name:      str = "gemma-4-31b-it",
        output_dir:      str = "./magi_outputs",
        system_prompt:   Optional[str] = None,
        temperature:     float = 0.7,
    ):
        self.api             = tool_api
        self.kg              = lean_kg
        self.sandbox         = sandbox
        self.fatigue_mon     = fatigue_monitor
        self.model_name      = model_name
        self.output_dir      = output_dir
        self.temperature     = temperature

        # Gemini client
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY not set. Create a .env file with:\n"
                "GOOGLE_API_KEY=your_key_here\n"
                "Or set the environment variable directly."
            )
        self.client = genai.Client(api_key=api_key)

        # Conversation state
        self._history: List[genai_types.Content] = []
        self._trace: List[AgentTraceEntry] = []
        self._baseline_kpis: Optional[Dict] = None
        self._last_intervention_sim_t: float = -9999.0
        self._intervention_count: int = 0
        self._message_callback = None  # set via set_message_callback()

        # Build system prompt with KG method list
        method_list = ", ".join(self.kg.get_all_method_names()) \
                      if self.kg._methods else "None loaded"
        self._system_prompt = (
            system_prompt if system_prompt
            else _MAGI_SYSTEM_PROMPT.format(method_list=method_list)
        )

        # Build tool declarations
        self._tools = self._build_tool_declarations()

        print(f"[CognitiveAgent] Initialised with model={model_name}, "
              f"{len(self.kg._methods)} lean methods in KG.")

    def set_message_callback(self, callback) -> None:
        """
        Set a callback invoked during monitor_cycle for each step.
        Signature: callback(event_type: str, data: dict) -> None
        event_types: 'thinking', 'tool_call', 'tool_result', 'response', 'error'
        """
        self._message_callback = callback

    def _emit(self, event_type: str, data: dict) -> None:
        """Emit a monitoring event via the callback if set."""
        if self._message_callback:
            try:
                self._message_callback(event_type, data)
            except Exception:
                pass

    # ── Tool declarations for Gemini ──────────────────────────────────

    def _build_tool_declarations(self) -> List[genai_types.Tool]:
        decls = [
            genai_types.FunctionDeclaration(
                name="get_current_kpis",
                description="Get all current KPIs (operational, physiological, lean) from the simulation.",
                parameters=genai_types.Schema(type="OBJECT", properties={}),
            ),
            genai_types.FunctionDeclaration(
                name="set_robot_speed_factor",
                description="Set robot speed multiplier. Range [0.5, 2.0]. 1.0=baseline. Higher=faster robot, shorter recovery for human.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "factor": genai_types.Schema(type="NUMBER", description="Speed factor"),
                }, required=["factor"]),
            ),
            genai_types.FunctionDeclaration(
                name="assign_workers",
                description="Assign workers to workstations. Workers: 001-004. Changes physiological profiles.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "cw_worker_id": genai_types.Schema(type="STRING", description="Worker ID for CW"),
                    "mw_worker_id": genai_types.Schema(type="STRING", description="Worker ID for MW"),
                }, required=["cw_worker_id", "mw_worker_id"]),
            ),
            genai_types.FunctionDeclaration(
                name="set_takt_time",
                description="Set takt time (product arrival interval) in seconds. Range [20, 300]. Lower=faster pace.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "takt_seconds": genai_types.Schema(type="NUMBER", description="Takt time in seconds"),
                }, required=["takt_seconds"]),
            ),
            genai_types.FunctionDeclaration(
                name="set_buffer_capacity",
                description="Set inter-station buffer capacity (WIP). Range [1, 20].",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "capacity": genai_types.Schema(type="INTEGER", description="Buffer capacity"),
                }, required=["capacity"]),
            ),
            genai_types.FunctionDeclaration(
                name="get_config_snapshot",
                description="Get current simulation configuration parameters.",
                parameters=genai_types.Schema(type="OBJECT", properties={}),
            ),
            genai_types.FunctionDeclaration(
                name="retrieve_lean_methods",
                description="Query the Lean Knowledge Graph for methods applicable to current KPI state. Returns ranked methods with trigger conditions.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "top_n": genai_types.Schema(type="INTEGER", description="Max methods to return (default 5)"),
                }),
            ),
            genai_types.FunctionDeclaration(
                name="get_lean_method_detail",
                description="Get full detail about a specific lean method by name (e.g. 'Heijunka', 'VSM', 'Muri', 'Ishikawa').",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "method_name": genai_types.Schema(type="STRING", description="Lean method name or alias"),
                }, required=["method_name"]),
            ),
            genai_types.FunctionDeclaration(
                name="execute_python_code",
                description="Execute Python code for analysis, OR-Tools optimisation, or matplotlib visualisation. Save plots to _OUTPUT_DIR.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "code":        genai_types.Schema(type="STRING", description="Python source code"),
                    "description": genai_types.Schema(type="STRING", description="What the code does"),
                }, required=["code"]),
            ),
            genai_types.FunctionDeclaration(
                name="get_fatigue_status",
                description="Get current fatigue classification for all active workers with physiological details.",
                parameters=genai_types.Schema(type="OBJECT", properties={}),
            ),
            genai_types.FunctionDeclaration(
                name="log_reasoning",
                description="Log your reasoning, observations, or notes for post-run review.",
                parameters=genai_types.Schema(type="OBJECT", properties={
                    "reasoning": genai_types.Schema(type="STRING", description="Your reasoning text"),
                }, required=["reasoning"]),
            ),
        ]
        return [genai_types.Tool(function_declarations=decls)]

    # ── Tool dispatch ─────────────────────────────────────────────────

    def _dispatch_tool(
        self,
        name: str,
        args: Dict[str, Any],
        live_physio: Optional[List] = None,
        live_task_log: Optional[List] = None,
    ) -> Any:
        """Route a tool call to the appropriate handler."""
        if name == "get_current_kpis":
            # Compute live KPIs if we have live data
            if live_task_log is not None and live_physio is not None:
                return self._compute_live_kpis(live_task_log, live_physio)
            return self.api.get_current_kpis()
        elif name == "set_robot_speed_factor":
            return self.api.set_robot_speed_factor(float(args.get("factor", 1.0)))
        elif name == "assign_workers":
            return self.api.assign_workers(
                str(args.get("cw_worker_id", "001")),
                str(args.get("mw_worker_id", "001")),
            )
        elif name == "set_takt_time":
            return self.api.set_takt_time(float(args.get("takt_seconds", 60.0)))
        elif name == "set_buffer_capacity":
            return self.api.set_buffer_capacity(int(args.get("capacity", 5)))
        elif name == "get_config_snapshot":
            return self.api.get_config_snapshot()
        elif name == "retrieve_lean_methods":
            kpis = self._compute_live_kpis(live_task_log, live_physio) \
                   if live_task_log else (self.api.get_current_kpis() or {}).get("kpis", {})
            if isinstance(kpis, dict) and "kpis" in kpis:
                kpis = kpis["kpis"]
            return self.kg.retrieve_by_kpi_state(
                kpis, self._baseline_kpis, int(args.get("top_n", 5)),
            )
        elif name == "get_lean_method_detail":
            return self.kg.retrieve_by_method_name(str(args.get("method_name", "")))
        elif name == "execute_python_code":
            return self.sandbox.execute(
                str(args.get("code", "")), str(args.get("description", "")),
            )
        elif name == "get_fatigue_status":
            if live_physio:
                return self.fatigue_mon.assess(live_physio, self.api.dt.config)
            return {"status": "no_live_data"}
        elif name == "log_reasoning":
            reasoning = str(args.get("reasoning", ""))
            print(f"  [Agent Reasoning] {reasoning[:200]}")
            return {"logged": True}
        else:
            return {"error": f"Unknown tool: {name}"}

    def _compute_live_kpis(
        self, task_log: List, physio_log: List
    ) -> Dict[str, Any]:
        """Compute approximate KPIs from live in-progress logs."""
        if not task_log:
            return {}
        last_time = task_log[-1].phase_end_time if task_log else 1.0
        hours = max(last_time / 3600.0, 0.001)

        cw_complete = {tr.product_id for tr in task_log
                       if tr.workstation == "CW" and tr.task_label == "05_pick_leave"}
        mw_complete = {tr.product_id for tr in task_log
                       if tr.workstation == "MW" and tr.task_label == "07_bag_leave"}

        cw_cycles_d = defaultdict(list)
        for tr in task_log:
            if tr.workstation == "CW":
                cw_cycles_d[tr.product_id].append(tr.phase_duration)
        cw_cts = [sum(ds) for pid, ds in cw_cycles_d.items() if len(ds) == 5]

        mw_cycles_d = defaultdict(list)
        for tr in task_log:
            if tr.workstation == "MW":
                mw_cycles_d[tr.product_id].append(tr.phase_duration)
        mw_cts = [sum(ds) for pid, ds in mw_cycles_d.items() if len(ds) == 2]

        cw_busy = sum(tr.phase_duration for tr in task_log if tr.workstation == "CW")
        mw_busy = sum(tr.phase_duration for tr in task_log if tr.workstation == "MW")
        robot_busy = sum(tr.phase_duration for tr in task_log
                         if tr.workstation == "CW" and tr.is_robot_phase)

        cw_hr = [r.hr_bpm for r in physio_log if r.workstation == "CW"] or [0]
        mw_hr = [r.hr_bpm for r in physio_log if r.workstation == "MW"] or [0]
        fatigue = [r.fatigue_score for r in physio_log] or [0]

        return {
            "kpis": {
                "total_units_produced":      len(mw_complete),
                "throughput_units_per_hour":  round(len(mw_complete) / hours, 2),
                "cw_mean_cycle_time_s":       round(float(np.mean(cw_cts)), 2) if cw_cts else 0,
                "mw_mean_cycle_time_s":       round(float(np.mean(mw_cts)), 2) if mw_cts else 0,
                "cw_utilisation_pct":         round(cw_busy / (last_time + 0.01) * 100, 2),
                "mw_utilisation_pct":         round(mw_busy / (last_time + 0.01) * 100, 2),
                "robot_utilisation_pct":      round(robot_busy / (last_time + 0.01) * 100, 2),
                "cw_mean_hr_bpm":             round(float(np.mean(cw_hr)), 2),
                "mw_mean_hr_bpm":             round(float(np.mean(mw_hr)), 2),
                "mean_fatigue_score":         round(float(np.mean(fatigue)), 4),
                "peak_fatigue_score":         round(float(max(fatigue)), 4),
                "oee":                        round(min(
                    (cw_busy + mw_busy) / (2 * last_time + 0.01) + 0.05, 1.0
                ) * min(len(mw_complete) / max(last_time / 60.0, 1), 1.0), 4),
                "line_balance_ratio":         round(
                    min(float(np.mean(cw_cts)) if cw_cts else 1,
                        float(np.mean(mw_cts)) if mw_cts else 1)
                    / max(float(np.mean(cw_cts)) if cw_cts else 1,
                          float(np.mean(mw_cts)) if mw_cts else 1, 0.01), 4),
            },
            "sim_time_s": round(last_time, 1),
            "sim_time_hours": round(hours, 3),
            "config": self.api.get_config_snapshot(),
        }

    # ── Main monitoring cycle ─────────────────────────────────────────

    def monitor_cycle(
        self,
        env:           Any,
        task_log:      List,
        physio_log:    List,
        user_messages: Optional[List[str]] = None,
    ) -> None:
        """
        Execute one agent monitoring cycle. Called periodically from the
        simulation's step_callback during real-time mode.
        """
        sim_t = env.now
        user_messages = user_messages or []

        # Build state summary
        state = self._compute_live_kpis(task_log, physio_log)
        fatigue = self.fatigue_mon.assess(physio_log, self.api.dt.config)
        state["fatigue_status"] = fatigue

        # Determine trigger
        trigger = "auto_monitor"
        if user_messages:
            trigger = "user_message"
        elif any(w.get("needs_intervention") for w in fatigue.get("workers", {}).values()):
            trigger = "fatigue_alert"

        # Build the user message for this cycle
        cycle_msg_parts = [
            f"[Monitoring Cycle — Sim time: {sim_t/3600:.2f}h ({sim_t:.0f}s)]",
            f"Current KPIs: {json.dumps(state.get('kpis', {}), indent=2)}",
            f"Config: {json.dumps(state.get('config', {}), indent=2)}",
            f"Fatigue: {json.dumps(fatigue, indent=2)}",
        ]
        if self._baseline_kpis:
            cycle_msg_parts.append(
                f"Baseline KPIs (for comparison): {json.dumps(self._baseline_kpis, indent=2)}"
            )
        if user_messages:
            for um in user_messages:
                cycle_msg_parts.append(f"\n[USER MESSAGE]: {um}")
        if trigger == "fatigue_alert":
            cycle_msg_parts.append(
                "\n⚠️ FATIGUE ALERT: One or more workers show elevated fatigue. "
                "Assess the situation and consider intervention."
            )

        cycle_text = "\n".join(cycle_msg_parts)

        # Add to conversation history
        self._history.append(genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=cycle_text)],
        ))

        # Truncate history if too long (keep system prompt effective)
        if len(self._history) > 40:
            self._history = self._history[-30:]

        # ── Call LLM with agentic tool-use loop ───────────────────────
        trace_tool_calls = []
        trace_tool_results = []
        trace_files = []
        agent_text = ""

        try:
            max_turns = 8  # max tool-use rounds per cycle
            for turn in range(max_turns):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=self._history,
                    config=genai_types.GenerateContentConfig(
                        tools=self._tools,
                        system_instruction=self._system_prompt,
                        temperature=self.temperature,
                    ),
                )

                if not response.candidates:
                    agent_text += "[No response from model]"
                    break

                candidate = response.candidates[0]
                parts = candidate.content.parts if candidate.content else []

                # Collect text parts
                text_parts = [p.text for p in parts if p.text]
                if text_parts:
                    combined_text = "\n".join(text_parts)
                    agent_text += combined_text
                    print(f"\n  [MAGI Agent] {combined_text[:500]}")
                    self._emit('thinking', {'text': combined_text, 'turn': turn})

                # Check for function calls
                fc_parts = [p for p in parts if p.function_call]
                if not fc_parts:
                    # No more tool calls — agent is done
                    self._history.append(candidate.content)
                    break

                # Add assistant's message (with function calls) to history
                self._history.append(candidate.content)

                # Execute each function call
                fn_responses = []
                for p in fc_parts:
                    fc = p.function_call
                    fn_name = fc.name
                    fn_args = dict(fc.args) if fc.args else {}
                    print(f"  [Tool Call] {fn_name}({json.dumps(fn_args)[:200]})")

                    self._emit('tool_call', {'name': fn_name, 'args': fn_args})
                    result = self._dispatch_tool(
                        fn_name, fn_args,
                        live_physio=physio_log,
                        live_task_log=task_log,
                    )
                    trace_tool_calls.append({"name": fn_name, "args": fn_args})
                    trace_tool_results.append({"name": fn_name, "result": result})
                    self._emit('tool_result', {'name': fn_name, 'result': result})

                    # Track files
                    if isinstance(result, dict) and "files_created" in result:
                        trace_files.extend(result["files_created"])

                    result_str = json.dumps(result, default=str)[:4000]
                    fn_responses.append(genai_types.Part.from_function_response(
                        name=fn_name, response={"result": result_str},
                    ))

                # Add function responses to history
                self._history.append(genai_types.Content(
                    role="user", parts=fn_responses,
                ))
            else:
                agent_text += "\n[Max tool-use rounds reached]"

        except Exception as e:
            error_msg = f"[Agent error: {e}]"
            print(f"  {error_msg}")
            agent_text += f"\n{error_msg}"
            traceback.print_exc()
            self._emit('error', {'error': error_msg})

        self._emit('response', {'text': agent_text, 'trigger': trigger,
                                'tool_calls': trace_tool_calls,
                                'sim_time_s': sim_t})

        # ── Log trace entry ───────────────────────────────────────────
        self._trace.append(AgentTraceEntry(
            sim_time_s=sim_t,
            wall_time=pd.Timestamp.now().isoformat(),
            trigger=trigger,
            state_summary=state,
            user_message=user_messages[0] if user_messages else None,
            agent_text=agent_text,
            tool_calls=trace_tool_calls,
            tool_results=trace_tool_results,
            files_created=trace_files,
        ))

    def set_baseline_kpis(self, kpis: Dict[str, Any]) -> None:
        """Store baseline KPIs for comparison during monitoring."""
        self._baseline_kpis = kpis

    # ── Post-run outputs ──────────────────────────────────────────────

    def get_trace(self) -> List[AgentTraceEntry]:
        return self._trace

    def save_trace(self, path: str) -> None:
        """Save full agent trace to JSON for post-run review."""
        entries = []
        for t in self._trace:
            entries.append({
                "sim_time_s":    t.sim_time_s,
                "sim_time_h":    round(t.sim_time_s / 3600, 3),
                "wall_time":     t.wall_time,
                "trigger":       t.trigger,
                "user_message":  t.user_message,
                "agent_text":    t.agent_text,
                "tool_calls":    t.tool_calls,
                "tool_results_summary": [
                    {"name": tr["name"], "result_preview": str(tr["result"])[:500]}
                    for tr in t.tool_results
                ],
                "files_created": t.files_created,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)
        print(f"[Agent] Trace saved to {path} ({len(entries)} entries)")

    def print_trace_summary(self) -> None:
        """Print a readable summary of all agent actions."""
        sep = "-" * 70
        print(f"\n{sep}")
        print("  MAGI COGNITIVE AGENT -- POST-RUN TRACE SUMMARY")
        print(sep)
        for i, t in enumerate(self._trace):
            print(f"\n  +- Cycle {i+1} @ sim_t={t.sim_time_s/3600:.2f}h "
                  f"[{t.trigger}]")
            if t.user_message:
                print(f"  | User: {t.user_message[:100]}")
            if t.tool_calls:
                for tc in t.tool_calls:
                    print(f"  | Tool: {tc['name']}({str(tc['args'])[:80]})")
            if t.files_created:
                for fp in t.files_created:
                    print(f"  | File: {fp}")
            if t.agent_text:
                # Show first 200 chars of agent's response
                preview = t.agent_text.strip()[:200].replace("\n", " ")
                print(f"  | Response: {preview}")
            print(f"  +{'-' * 60}")
        print(f"\n  Total cycles: {len(self._trace)}")
        print(sep)


# ─────────────────────────────────────────────────────────────────────────────
