import os
import json
from typing import Dict, List, Any, Optional

from magi.physical.constants import _KG_METRIC_TO_KPI



class LeanKGRetriever:
    """
    Retrieves contextually relevant Lean methodologies from the Knowledge
    Graph based on the current simulation state.

    This is a structured RAG approach: instead of embedding-based similarity
    search, it matches the KG's own encoded trigger_conditions against live
    KPI values. This ensures every retrieved method is domain-logically
    relevant rather than just semantically similar.
    """

    def __init__(self, kg_dir: str = "./lean_kg_output"):
        self.nodes: List[Dict]  = []
        self.edges: List[Dict]  = []
        self._methods: Dict[str, Dict] = {}   # id → node
        self._problems: Dict[str, Dict] = {}  # id → node
        self._all_nodes: Dict[str, Dict] = {} # id → node
        self._load(kg_dir)

    def _load(self, kg_dir: str) -> None:
        nodes_path = os.path.join(kg_dir, "nodes.json")
        edges_path = os.path.join(kg_dir, "edges.json")
        if not os.path.exists(nodes_path):
            print(f"[KG] WARNING: {nodes_path} not found. RAG disabled.")
            return
        with open(nodes_path, "r", encoding="utf-8") as f:
            self.nodes = json.load(f)
        with open(edges_path, "r", encoding="utf-8") as f:
            self.edges = json.load(f)
        for n in self.nodes:
            nid = n.get("id", "")
            self._all_nodes[nid] = n
            if n.get("type") == "lean_method":
                self._methods[nid] = n
            elif n.get("type") == "problem_type":
                self._problems[nid] = n
        print(f"[KG] Loaded {len(self._methods)} lean methods, "
              f"{len(self._problems)} problem types, {len(self.edges)} edges.")

    # ── Public retrieval methods ──────────────────────────────────────

    def retrieve_by_kpi_state(
        self,
        kpis: Dict[str, Any],
        baseline_kpis: Optional[Dict[str, Any]] = None,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Find lean methods whose trigger conditions match the current KPIs.
        Returns a list of dicts with method info and matched triggers.
        """
        candidates = []
        for mid, node in self._methods.items():
            triggers = node.get("trigger_conditions", [])
            for trig in triggers:
                metric = trig.get("metric", "")
                kpi_key = _KG_METRIC_TO_KPI.get(metric)
                if kpi_key is None or kpi_key not in kpis:
                    continue
                current_val = kpis[kpi_key]
                # Scale conversions
                if metric in ("mw_utilization", "cw_utilization", "robot_utilization"):
                    current_val = current_val / 100.0
                if metric == "fatigue_score":
                    current_val = current_val * 100.0  # KG uses 0-100

                threshold_type = trig.get("threshold_type", "absolute")
                threshold = trig.get("threshold", 0)
                op = trig.get("operator", ">")

                if threshold_type == "pct_of_baseline" and baseline_kpis:
                    base_val = baseline_kpis.get(kpi_key, 0)
                    if metric in ("mw_utilization", "cw_utilization", "robot_utilization"):
                        base_val = base_val / 100.0
                    if metric == "fatigue_score":
                        base_val = base_val * 100.0
                    effective_threshold = base_val * threshold
                else:
                    effective_threshold = threshold

                triggered = False
                if op == ">" and current_val > effective_threshold:
                    triggered = True
                elif op == "<" and current_val < effective_threshold:
                    triggered = True
                elif op == ">=" and current_val >= effective_threshold:
                    triggered = True
                elif op == "<=" and current_val <= effective_threshold:
                    triggered = True

                if triggered:
                    candidates.append({
                        "method_id":   mid,
                        "label":       node.get("label", mid),
                        "priority":    trig.get("priority", 0),
                        "trigger":     trig.get("description", ""),
                        "category":    node.get("lean_category", ""),
                        "description": node.get("description", ""),
                        "adjustments": node.get("simulation_adjustments", []),
                        "impacts":     node.get("expected_kpi_impacts", []),
                        "references":  node.get("references", []),
                    })

        # Sort by priority descending, deduplicate by method_id keeping highest
        seen = set()
        unique = []
        for c in sorted(candidates, key=lambda x: x["priority"], reverse=True):
            if c["method_id"] not in seen:
                seen.add(c["method_id"])
                unique.append(c)
        return unique[:top_n]

    def retrieve_by_method_name(self, name: str) -> Optional[Dict]:
        """Fuzzy-match a lean method by label or alias."""
        name_lower = name.lower()
        for mid, node in self._methods.items():
            labels = [node.get("label", "").lower()] + \
                     [a.lower() for a in node.get("aka", [])]
            if any(name_lower in lb for lb in labels) or name_lower == mid:
                return self.get_full_context_for_method(mid)
        return None

    def retrieve_by_problem_type(self, problem_id: str) -> List[Dict]:
        """Find all methods that ADDRESS a given problem type."""
        methods = []
        for edge in self.edges:
            if edge.get("target") == problem_id and \
               edge.get("relation") == "ADDRESSES":
                mid = edge.get("source")
                if mid in self._methods:
                    methods.append({
                        "method_id": mid,
                        "label":     self._methods[mid].get("label", mid),
                        "weight":    edge.get("weight", 0),
                    })
        return sorted(methods, key=lambda x: x["weight"], reverse=True)

    def get_full_context_for_method(self, method_id: str) -> Optional[Dict]:
        """Return complete method node + all connected edges + neighbour nodes."""
        node = self._methods.get(method_id)
        if node is None:
            return None
        connected_edges = [e for e in self.edges
                           if e.get("source") == method_id
                           or e.get("target") == method_id]
        neighbour_ids = set()
        for e in connected_edges:
            neighbour_ids.add(e.get("source"))
            neighbour_ids.add(e.get("target"))
        neighbour_ids.discard(method_id)
        neighbours = {nid: self._all_nodes[nid]
                      for nid in neighbour_ids if nid in self._all_nodes}
        return {
            "method":     node,
            "edges":      connected_edges,
            "neighbours": neighbours,
        }

    def get_all_method_names(self) -> List[str]:
        """Return list of all lean method labels for the system prompt."""
        return [n.get("label", n.get("id")) for n in self._methods.values()]

    def get_method_summary_text(self) -> str:
        """One-liner per method for embedding in the system prompt."""
        lines = []
        for mid, n in self._methods.items():
            lines.append(f"- {n.get('label', mid)}: {n.get('description', '')[:120]}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
