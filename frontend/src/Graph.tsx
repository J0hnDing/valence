import { useMemo, useState } from 'react';
import dagre from '@dagrejs/dagre';
import { Background, Controls, Handle, MiniMap, Position, ReactFlow, ReactFlowProvider, useReactFlow, type Node, type NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { displayJson, Empty, label, number } from './components';
import type { TraceGraph, TraceNode } from './types';

export function output(value: unknown): string {
  if (typeof value === 'number') return number(value);
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return displayJson(value);
  return String(value);
}
type ComputationNode = Node<{ trace: TraceNode }, 'computation'>;
function Computation({ data, selected }: NodeProps<ComputationNode>) {
  const trace = data.trace;
  return <div className={`computation-node ${selected ? 'selected' : ''} kind-${trace.kind}`}>
    <Handle type="target" position={Position.Left} />
    <div className="node-kind">{label(trace.kind)}</div><div className="node-label">{trace.label}</div><div className="node-value">{output(trace.value)}</div>
    <Handle type="source" position={Position.Right} />
  </div>;
}
const nodeTypes = { computation: Computation };
export function TraceInspector({ node }: { node?: TraceNode }) {
  return <aside className="trace-inspector" aria-label="Node inspector">{node ? <>
    <span className="eyebrow">{label(node.kind)} / {node.id}</span><h3>{node.label}</h3>
    <div className="inspector-output"><span>Output</span><strong>{output(node.value)}</strong></div>
    <h4>Definition</h4><p>{node.definition || 'No additional definition supplied.'}</p>
    <h4>Inputs</h4><Values values={node.inputs} />
    <h4>Parameters</h4><Values values={node.parameters} />
    <h4>Formula</h4><code className="formula">{node.formula || 'Input value (no transformation)'}</code>
    {node.note && <><h4>Caller-supplied note</h4><p className="caller-note">{node.note}</p></>}
  </> : <Empty>Select a computation node to inspect its definition, exact inputs, parameters, formula and output.</Empty>}</aside>;
}
function Values({ values }: { values: Record<string, unknown> }) {
  if (!Object.keys(values).length) return <p className="muted small">None</p>;
  return <dl className="trace-values">{Object.entries(values).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{output(value)}</dd></div>)}</dl>;
}
function GraphCanvas({ graph }: { graph: TraceGraph }) {
  const [selectedId, setSelectedId] = useState(''); const [query, setQuery] = useState('');
  const flow = useReactFlow<ComputationNode>();
  const { nodes, edges } = useMemo(() => {
    const layout = new dagre.graphlib.Graph();
    layout.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 90 }); layout.setDefaultEdgeLabel(() => ({}));
    graph.nodes.forEach(node => layout.setNode(node.id, { width: 218, height: 96 }));
    graph.edges.forEach(edge => layout.setEdge(edge.source, edge.target)); dagre.layout(layout);
    return {
      nodes: graph.nodes.map(trace => { const position = layout.node(trace.id); return { id: trace.id, type: 'computation' as const, position: { x: position.x - 109, y: position.y - 48 }, data: { trace } }; }),
      edges: graph.edges.map((edge, index) => ({ id: `${edge.source}-${edge.target}-${index}`, ...edge, style: { stroke: '#51626c', strokeWidth: 1.2 } })),
    };
  }, [graph]);
  const visibleNodes = nodes.map(node => ({ ...node, selected: node.id === selectedId }));
  const filtered = graph.nodes.filter(node => `${node.label} ${node.kind} ${node.id}`.toLowerCase().includes(query.toLowerCase()));
  function focus(id: string) {
    setSelectedId(id);
    const selected = nodes.find(node => node.id === id);
    if (selected) void flow.setCenter(selected.position.x + 109, selected.position.y + 48, { zoom: 1, duration: 0 });
  }
  return <div className="graph-section">
    <div className="graph-toolbar"><span className="muted">{graph.nodes.length} nodes · {graph.edges.length} dependencies</span><input aria-label="Find graph node" value={query} onChange={event => setQuery(event.target.value)} placeholder="Find a computation…" /><select aria-label="Select graph node" value={selectedId} onChange={event => focus(event.target.value)}><option value="">Inspect node…</option>{filtered.map(node => <option key={node.id} value={node.id}>{node.label} · {output(node.value)}</option>)}</select><button onClick={() => { void flow.fitView({ padding: 0.15, duration: 0 }); }}>Fit all</button></div>
    <div className="graph-and-inspector"><div className="flow-canvas" aria-label="Complete backend computation graph">
      <ReactFlow nodes={visibleNodes} edges={edges} nodeTypes={nodeTypes} fitView minZoom={0.025} maxZoom={2} nodesDraggable={false} nodesConnectable={false} elementsSelectable={true} onNodeClick={(_, node) => setSelectedId(node.id)} onPaneClick={() => setSelectedId('')} colorMode="dark" fitViewOptions={{ padding: 0.15 }}>
        <Background color="#343d43" gap={22} /><Controls showInteractive={false} /><MiniMap nodeColor="#447363" maskColor="rgba(10,13,15,0.65)" pannable zoomable />
      </ReactFlow>
    </div><TraceInspector node={graph.nodes.find(node => node.id === selectedId)} /></div>
    <p className="small muted">Scroll to zoom · drag the canvas to pan · use the node selector to focus any computation. Graph values and dependencies are supplied by the backend.</p>
  </div>;
}
export function ComputationGraph({ graph }: { graph: TraceGraph }) { return <ReactFlowProvider><GraphCanvas graph={graph} /></ReactFlowProvider>; }
