"""
MAGI Meta Layer — Lean Knowledge Graph Router.

Endpoints for the Lean KG visualization and querying:
  GET  /api/lean/graph            — full graph (nodes + edges)
  GET  /api/lean/methods          — list all lean methods
  GET  /api/lean/method/{id}      — full method detail
  POST /api/lean/query            — query methods by KPI state
  GET  /api/lean/problems         — list all problem types
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Lazy-loaded singleton KG
_kg = None

def _get_kg():
    global _kg
    if _kg is None:
        try:
            from magi.cognitive.lean_kg import LeanKGRetriever
            _kg = LeanKGRetriever()
        except Exception as e:
            print(f"[lean router] KG load failed: {e}")
            _kg = None
    return _kg


class KpiQueryRequest(BaseModel):
    kpis: Dict[str, Any]
    baseline_kpis: Optional[Dict[str, Any]] = None
    top_n: int = 5


@router.get("/graph")
async def get_graph():
    """Return the full Knowledge Graph (nodes and edges) for D3 visualization."""
    kg = _get_kg()
    if kg is None:
        return {"nodes": [], "edges": [], "error": "KG not loaded — check lean_kg_output/"}
    return {
        "nodes": kg.nodes,
        "edges": kg.edges,
        "meta": {
            "method_count":  len(kg._methods),
            "problem_count": len(kg._problems),
            "edge_count":    len(kg.edges),
        }
    }


@router.get("/methods")
async def list_methods():
    """List all lean method nodes (summary, not full context)."""
    kg = _get_kg()
    if kg is None:
        return {"methods": []}
    methods = []
    for mid, node in kg._methods.items():
        methods.append({
            "id":          mid,
            "label":       node.get("label", mid),
            "category":    node.get("lean_category", ""),
            "description": node.get("description", "")[:200],
            "waste_types": node.get("waste_types", []),
            "aka":         node.get("aka", []),
        })
    return {"methods": sorted(methods, key=lambda m: m["label"])}


@router.get("/method/{method_id}")
async def get_method_detail(method_id: str):
    """Get full detail for a lean method including edges and neighbours."""
    kg = _get_kg()
    if kg is None:
        raise HTTPException(status_code=503, detail="KG not loaded")
    detail = kg.get_full_context_for_method(method_id)
    if detail is None:
        # Try fuzzy match by label
        detail = kg.retrieve_by_method_name(method_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Method '{method_id}' not found")
    return detail


@router.get("/problems")
async def list_problems():
    """List all problem type nodes."""
    kg = _get_kg()
    if kg is None:
        return {"problems": []}
    problems = [
        {
            "id":          pid,
            "label":       node.get("label", pid),
            "description": node.get("description", ""),
            "category":    node.get("category", ""),
        }
        for pid, node in kg._problems.items()
    ]
    return {"problems": sorted(problems, key=lambda p: p["label"])}


@router.post("/query")
async def query_by_kpis(req: KpiQueryRequest):
    """Find lean methods triggered by the given KPI state."""
    kg = _get_kg()
    if kg is None:
        return {"triggered": [], "error": "KG not loaded"}
    triggered = kg.retrieve_by_kpi_state(req.kpis, req.baseline_kpis, req.top_n)
    return {"triggered": triggered, "count": len(triggered)}


@router.get("/search")
async def search_methods(q: str):
    """Search methods by name/alias."""
    kg = _get_kg()
    if kg is None:
        return {"results": []}
    q_lower = q.lower()
    results = []
    for mid, node in kg._methods.items():
        label = node.get("label", "").lower()
        desc  = node.get("description", "").lower()
        aka   = [a.lower() for a in node.get("aka", [])]
        if q_lower in label or q_lower in desc or any(q_lower in a for a in aka):
            results.append({
                "id":          mid,
                "label":       node.get("label", mid),
                "category":    node.get("lean_category", ""),
                "description": node.get("description", "")[:200],
            })
    return {"results": results[:20]}
