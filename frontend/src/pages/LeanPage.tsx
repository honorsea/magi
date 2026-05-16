import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '../api/client';
import { Search, X } from 'lucide-react';

// ── D3 Force Graph ─────────────────────────────────────────────────────────────

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: string;          // "lean_method" | "problem_type" | "kpi"
  lean_category?: string;
  description?: string;
}

interface GraphEdge extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  relation: string;
  weight?: number;
}

const NODE_COLORS: Record<string, string> = {
  lean_method:  'hsl(217, 80%, 55%)',
  problem_type: 'hsl(0,   70%, 55%)',
  kpi:          'hsl(142, 65%, 45%)',
  default:      'hsl(220, 15%, 60%)',
};

const KG_CATEGORIES: Record<string, string> = {
  'Pull System':       'hsl(217, 80%, 55%)',
  'Waste Reduction':   'hsl(35,  80%, 50%)',
  'Quality':           'hsl(142, 65%, 45%)',
  'Flow':              'hsl(262, 70%, 55%)',
  'People':            'hsl(0,   70%, 55%)',
  'Standardization':   'hsl(180, 60%, 45%)',
};

// ── Method Detail Panel ───────────────────────────────────────────────────────

const MethodDetail: React.FC<{ node: GraphNode | null; onClose: () => void }> = ({ node, onClose }) => {
  const [detail, setDetail] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!node || node.type !== 'lean_method') { setDetail(null); return; }
    setLoading(true);
    api.lean.getMethod(node.id).then(d => { setDetail(d); setLoading(false); }).catch(() => setLoading(false));
  }, [node?.id]);

  if (!node) return null;

  return (
    <div style={{
      position: 'absolute', right: 0, top: 0, width: '320px', height: '100%',
      background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', zIndex: 10
    }}>
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: '15px' }}>{node.label}</h3>
          <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px',
            background: KG_CATEGORIES[node.lean_category || ''] || 'var(--bg-tertiary)',
            color: 'white' }}>
            {node.lean_category || node.type}
          </span>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px' }}>
          <X size={18} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {loading && <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Loading…</div>}

        {detail?.method && (
          <>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: 0 }}>
              {detail.method.description}
            </p>

            {detail.method.aka?.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Also Known As</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                  {detail.method.aka.map((a: string) => (
                    <span key={a} style={{ fontSize: '11px', padding: '2px 6px', background: 'var(--bg-tertiary)',
                      borderRadius: '4px', color: 'var(--text-secondary)' }}>{a}</span>
                  ))}
                </div>
              </div>
            )}

            {detail.method.waste_types?.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Addresses Waste</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '4px' }}>
                  {detail.method.waste_types.map((w: string) => (
                    <span key={w} style={{ fontSize: '11px', padding: '2px 6px',
                      background: 'hsl(35,80%,90%)', color: 'hsl(35,80%,30%)', borderRadius: '4px' }}>{w}</span>
                  ))}
                </div>
              </div>
            )}

            {detail.method.simulation_adjustments?.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Simulation Adjustments</strong>
                {detail.method.simulation_adjustments.map((adj: any, i: number) => (
                  <div key={i} style={{ marginTop: '6px', padding: '8px', background: 'var(--bg-tertiary)',
                    borderRadius: '6px', fontSize: '12px' }}>
                    <div style={{ fontWeight: 600 }}>{adj.parameter}</div>
                    <div style={{ color: 'var(--text-secondary)' }}>{adj.description}</div>
                  </div>
                ))}
              </div>
            )}

            {detail.method.expected_kpi_impacts?.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Expected KPI Impacts</strong>
                {detail.method.expected_kpi_impacts.map((imp: any, i: number) => (
                  <div key={i} style={{ marginTop: '4px', fontSize: '12px', display: 'flex', justifyContent: 'space-between',
                    padding: '4px 8px', background: 'var(--bg-tertiary)', borderRadius: '4px' }}>
                    <span>{imp.kpi}</span>
                    <span style={{ color: imp.direction === 'increase' ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 600 }}>
                      {imp.direction === 'increase' ? '↑' : '↓'} {imp.magnitude}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {detail.method.references?.length > 0 && (
              <div>
                <strong style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>References</strong>
                {detail.method.references.map((ref: string, i: number) => (
                  <div key={i} style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{ref}</div>
                ))}
              </div>
            )}
          </>
        )}

        {!loading && !detail && node.type === 'problem_type' && (
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{node.description || 'No description available.'}</p>
        )}
      </div>
    </div>
  );
};

// ── Lean KG Page ──────────────────────────────────────────────────────────────

export const LeanPage: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [malformed, setMalformed] = useState<string | null>(null);
  const [diagnostic, setDiagnostic] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null);

  useEffect(() => {
    api.lean.getGraph()
      .then((payload: any) => {
        if (payload?.error) {
          setDiagnostic(`API returned an error payload: ${payload.error}`);
          setNodes([]);
          setEdges([]);
          setMeta(payload?.meta ?? null);
          setLoading(false);
          return;
        }
        if (!payload || !Array.isArray(payload.nodes) || !Array.isArray(payload.edges)) {
          setMalformed('Expected object with arrays at payload.nodes and payload.edges.');
          setLoading(false);
          return;
        }
        const { nodes: n, edges: e, meta: m } = payload;
        setNodes(n as GraphNode[]);
        setEdges(e as GraphEdge[]);
        setMeta(m);
        if ((n as GraphNode[]).length === 0) {
          setDiagnostic('Graph payload loaded, but nodes array is empty.');
        }
        setLoading(false);
      })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  useEffect(() => {
    if (nodes.length === 0 || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const rect = svgRef.current.getBoundingClientRect();
    const W = rect.width || 800;
    const H = rect.height || 600;

    // Filter nodes/edges by search & type
    const filteredNodes = nodes.filter(n => {
      const typeMatch = filterType === 'all' || n.type === filterType;
      const searchMatch = !search || n.label.toLowerCase().includes(search.toLowerCase());
      return typeMatch && searchMatch;
    });
    const filteredIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = edges.filter(e => {
      const sid = typeof e.source === 'object' ? (e.source as GraphNode).id : e.source;
      const tid = typeof e.target === 'object' ? (e.target as GraphNode).id : e.target;
      return filteredIds.has(sid) && filteredIds.has(tid);
    });

    // Zoom behaviour
    const g = svg.append('g');
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => g.attr('transform', event.transform.toString()));
    svg.call(zoom as any);

    // Arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#94a3b8');

    // Links
    const link = g.append('g').selectAll('line')
      .data(filteredEdges).enter().append('line')
      .attr('stroke', '#e2e8f0').attr('stroke-width', d => Math.max(0.5, (d.weight ?? 0.5) * 2))
      .attr('marker-end', 'url(#arrow)');

    // Node groups
    const nodeG = g.append('g').selectAll('g')
      .data(filteredNodes).enter().append('g')
      .attr('cursor', 'pointer')
      .on('click', (_, d) => setSelectedNode(d))
      .call(d3.drag<SVGGElement, GraphNode>()
        .on('start', (event, d) => {
          if (!event.active) simulationRef.current?.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulationRef.current?.alphaTarget(0);
          d.fx = null; d.fy = null;
        }) as any
      );

    nodeG.append('circle')
      .attr('r', d => d.type === 'lean_method' ? 8 : 6)
      .attr('fill', d => {
        if (d.lean_category && KG_CATEGORIES[d.lean_category]) return KG_CATEGORIES[d.lean_category];
        return NODE_COLORS[d.type] || NODE_COLORS.default;
      })
      .attr('stroke', 'white').attr('stroke-width', 2);

    nodeG.append('text')
      .attr('dx', 12).attr('dy', '0.35em')
      .attr('font-size', '10px')
      .attr('fill', 'var(--text-primary)')
      .text(d => d.label.length > 25 ? d.label.slice(0, 24) + '…' : d.label);

    // Force simulation
    const sim = d3.forceSimulation<GraphNode>(filteredNodes)
      .force('link', d3.forceLink<GraphNode, GraphEdge>(filteredEdges)
        .id(d => d.id).distance(80).strength(0.3))
      .force('charge', d3.forceManyBody().strength(-150))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(18))
      .on('tick', () => {
        link
          .attr('x1', d => (d.source as GraphNode).x ?? 0)
          .attr('y1', d => (d.source as GraphNode).y ?? 0)
          .attr('x2', d => (d.target as GraphNode).x ?? 0)
          .attr('y2', d => (d.target as GraphNode).y ?? 0);
        nodeG.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`);
      });

    simulationRef.current = sim;
    return () => { sim.stop(); };
  }, [nodes, edges, search, filterType]);

  if (loading) return (
    <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading Lean KG…</div>
  );

  if (error) return (
    <div style={{ padding: '40px' }}>
      <div style={{ padding: '16px', background: 'hsl(0,60%,97%)', border: '1px solid hsl(0,60%,85%)',
        borderRadius: '8px', color: 'var(--accent-red)' }}>
        Failed to load Lean Knowledge Graph: {error}
        <div style={{ fontSize: '12px', marginTop: '4px', color: 'var(--text-secondary)' }}>
          Ensure <code>lean_kg_output/nodes.json</code> and <code>edges.json</code> exist.
        </div>
      </div>
    </div>
  );
  if (malformed) return (
    <div style={{ padding: '40px' }}>
      <div style={{ padding: '16px', background: 'hsl(35,100%,96%)', border: '1px solid hsl(35,70%,80%)', borderRadius: '8px' }}>
        <strong>Malformed payload from Lean API</strong>
        <div style={{ marginTop: '8px', fontSize: '13px' }}>{malformed}</div>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <div>
          <h2 style={{ margin: 0 }}>Lean Knowledge Graph</h2>
          {meta && (
            <p style={{ margin: '2px 0 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
              {meta.method_count} methods · {meta.problem_count} problems · {meta.edge_count} edges
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Search */}
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)',
              color: 'var(--text-secondary)' }} />
            <input
              type="text" placeholder="Search methods…" value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: '30px', padding: '6px 10px 6px 30px', borderRadius: '6px',
                border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                color: 'var(--text-primary)', fontSize: '13px', width: '200px' }}
            />
          </div>
          {/* Filter */}
          <select value={filterType} onChange={e => setFilterType(e.target.value)}
            style={{ padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border)',
              background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '13px' }}>
            <option value="all">All nodes</option>
            <option value="lean_method">Methods only</option>
            <option value="problem_type">Problems only</option>
          </select>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', flexShrink: 0 }}>
        {Object.entries(KG_CATEGORIES).slice(0, 6).map(([cat, color]) => (
          <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: color, display: 'inline-block' }} />
            {cat}
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: NODE_COLORS.problem_type, display: 'inline-block' }} />
          Problem Type
        </div>
      </div>

      {/* Graph canvas area */}
      <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        {diagnostic && (
          <div style={{ marginBottom: '10px', padding: '12px', background: 'hsl(38,100%,96%)', border: '1px solid hsl(38,80%,78%)', borderRadius: '8px' }}>
            <div style={{ fontWeight: 600, marginBottom: '6px' }}>Lean graph diagnostics</div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{diagnostic}</div>
            <ul style={{ margin: '8px 0 0 18px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              <li>Checked endpoint: <code>/api/lean/graph</code></li>
              <li>Expected data path: <code>payload.nodes[]</code>, <code>payload.edges[]</code>, optional <code>payload.meta</code></li>
              <li>Action: verify Lean KG generation and API router health.</li>
            </ul>
          </div>
        )}
        <div className="card" style={{ width: '100%', height: '100%', overflow: 'hidden', padding: 0 }}>
          <svg ref={svgRef} width="100%" height="100%" />
        </div>
        <MethodDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>
    </div>
  );
};
