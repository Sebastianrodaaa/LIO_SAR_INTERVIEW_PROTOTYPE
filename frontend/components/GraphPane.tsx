"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent } from "react";

import type { GraphNode, GraphView } from "@/lib/types";

const KIND_FILL: Record<string, string> = {
  Employee: "#ffffff",
  Department: "#f2f2f7",
  Vendor: "#eef5ff",
  Policy: "#fff7e8",
};

const KIND_FILTER: { id: string; label: string; swatch: string }[] = [
  { id: "Employee", label: "People", swatch: "#ffffff" },
  { id: "Vendor", label: "Software", swatch: "#eef5ff" },
  { id: "Policy", label: "Rules", swatch: "#fff7e8" },
  { id: "Department", label: "Teams", swatch: "#f2f2f7" },
];

const WORLD = { w: 960, h: 620 };

type View = { x: number; y: number; w: number; h: number };

function nodeById(graph: GraphView, id: string) {
  return graph.nodes.find((n) => n.id === id);
}

function roleOf(kind: string) {
  if (kind === "Employee") return "Person";
  if (kind === "Vendor") return "Software";
  if (kind === "Policy") return "Rule";
  return "Team";
}

export function GraphPane({
  graph,
  caption,
  onAsk,
}: {
  graph: GraphView | null;
  caption: string;
  onAsk?: (node: GraphNode) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [view, setView] = useState<View>({ x: 0, y: 0, w: WORLD.w, h: WORLD.h });
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [kinds, setKinds] = useState<Record<string, boolean>>({
    Employee: true,
    Vendor: true,
    Policy: true,
    Department: true,
  });
  const drag = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: View;
    moved: boolean;
  } | null>(null);

  const visible = useMemo(() => {
    if (!graph) return { nodes: [] as GraphNode[], edges: graph?.edges ?? [] };
    const nodes = graph.nodes.filter((n) => kinds[n.kind] !== false);
    const ids = new Set(nodes.map((n) => n.id));
    const edges = graph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { nodes, edges };
  }, [graph, kinds]);

  const neighborIds = useMemo(() => {
    const focus = hoverId || selectedId;
    if (!focus || !graph) return new Set<string>();
    const next = new Set<string>([focus]);
    for (const edge of graph.edges) {
      if (edge.source === focus) next.add(edge.target);
      if (edge.target === focus) next.add(edge.source);
    }
    return next;
  }, [graph, hoverId, selectedId]);

  const selected = graph && selectedId ? nodeById(graph, selectedId) : undefined;

  const clientToWorld = useCallback(
    (clientX: number, clientY: number) => {
      const svg = svgRef.current;
      if (!svg) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      return {
        x: view.x + ((clientX - rect.left) / Math.max(rect.width, 1)) * view.w,
        y: view.y + ((clientY - rect.top) / Math.max(rect.height, 1)) * view.h,
      };
    },
    [view],
  );

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const world = clientToWorld(event.clientX, event.clientY);
      const factor = event.deltaY > 0 ? 1.1 : 0.9;
      const nextW = Math.min(1400, Math.max(320, view.w * factor));
      const nextH = nextW * (WORLD.h / WORLD.w);
      const nx = world.x - ((world.x - view.x) * nextW) / view.w;
      const ny = world.y - ((world.y - view.y) * nextH) / view.h;
      setView({ x: nx, y: ny, w: nextW, h: nextH });
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [clientToWorld, view]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!graph) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-[13px] leading-relaxed text-apple-muted">
        Loading the people, tools, and rules for this request…
      </div>
    );
  }

  const onPointerDown = (event: PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    drag.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: view,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent<SVGSVGElement>) => {
    const state = drag.current;
    if (!state || state.pointerId !== event.pointerId) return;
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const dx = ((event.clientX - state.startX) / Math.max(rect.width, 1)) * state.origin.w;
    const dy = ((event.clientY - state.startY) / Math.max(rect.height, 1)) * state.origin.h;
    if (Math.abs(event.clientX - state.startX) + Math.abs(event.clientY - state.startY) > 4) {
      state.moved = true;
    }
    if (state.moved) {
      setView({
        ...state.origin,
        x: state.origin.x - dx,
        y: state.origin.y - dy,
      });
    }
  };

  const onPointerUp = (event: PointerEvent<SVGSVGElement>) => {
    const state = drag.current;
    if (state && !state.moved && (event.target as Element).closest("[data-node]") == null) {
      setSelectedId(null);
    }
    drag.current = null;
  };

  const toggleKind = (id: string) => {
    setKinds((current) => {
      const next = { ...current, [id]: !current[id] };
      if (Object.values(next).every((v) => !v)) return current;
      return next;
    });
  };

  return (
    <div className="absolute inset-0 flex flex-col overflow-hidden">
      <p className="shrink-0 px-4 pb-1 pt-1 text-[12px] leading-snug text-apple-muted">{caption}</p>
      <div className="relative min-h-0 flex-1">
        <svg
          ref={svgRef}
          viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
          preserveAspectRatio="xMidYMid meet"
          className="h-full w-full touch-none"
          role="img"
          aria-label="Map of people, software, and company rules. Scroll to zoom, drag to pan, click a node to inspect."
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{ cursor: drag.current?.moved ? "grabbing" : "grab" }}
        >
          <defs>
            <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <path d="M 24 0 L 0 0 0 24" fill="none" stroke="rgba(0,0,0,0.035)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect
            x={view.x - 400}
            y={view.y - 400}
            width={view.w + 800}
            height={view.h + 800}
            fill="url(#grid)"
          />

          <RegionLabel x={88} y={188} text="Teams" />
          <RegionLabel x={268} y={22} text="People in the reporting line" />
          <RegionLabel x={430} y={348} text="Software options" />
          <RegionLabel x={730} y={198} text="Company rules" />

          {visible.edges.map((edge) => {
            const a = nodeById(graph, edge.source);
            const b = nodeById(graph, edge.target);
            if (!a || !b) return null;
            const hot =
              edge.active ||
              (hoverId != null && (edge.source === hoverId || edge.target === hoverId)) ||
              (selectedId != null && (edge.source === selectedId || edge.target === selectedId));
            const midX = (a.x + b.x) / 2;
            const midY = (a.y + b.y) / 2 - 12;
            return (
              <path
                key={`${edge.source}-${edge.target}-${edge.kind}`}
                d={`M ${a.x} ${a.y} Q ${midX} ${midY} ${b.x} ${b.y}`}
                fill="none"
                stroke={hot ? "#007AFF" : "rgba(0,0,0,0.14)"}
                strokeWidth={hot ? 2.2 : 1.2}
                strokeDasharray={hot ? "6 6" : edge.kind === "REPORTS_TO" ? "0" : "3 4"}
                className={hot ? "edge-active" : undefined}
                opacity={hoverId && !hot ? 0.22 : 1}
              />
            );
          })}

          {visible.nodes.map((node) => {
            const w = node.kind === "Employee" ? 176 : 156;
            const h = 54;
            const hot = node.active || node.id === hoverId || node.id === selectedId;
            const dim = Boolean((hoverId || selectedId) && !neighborIds.has(node.id) && !node.active);
            return (
              <g
                key={node.id}
                data-node={node.id}
                transform={`translate(${node.x - w / 2}, ${node.y - h / 2})`}
                className={node.active ? "node-active" : undefined}
                opacity={dim ? 0.32 : 1}
                style={{ cursor: "pointer" }}
                onPointerEnter={() => setHoverId(node.id)}
                onPointerLeave={() => setHoverId((id) => (id === node.id ? null : id))}
                onClick={(event) => {
                  event.stopPropagation();
                  if (drag.current?.moved) return;
                  setSelectedId(node.id);
                }}
              >
                <title>{inspectorTitle(node)}</title>
                <rect
                  width={w}
                  height={h}
                  rx="12"
                  fill={KIND_FILL[node.kind] ?? "#fff"}
                  stroke={
                    node.id === selectedId
                      ? "#007AFF"
                      : node.ooo
                        ? "#ff9f0a"
                        : hot
                          ? "#007AFF"
                          : "rgba(0,0,0,0.08)"
                  }
                  strokeWidth={hot || node.id === selectedId ? 2 : 1}
                  strokeDasharray={node.ooo ? "4 3" : undefined}
                />
                <text x={12} y={16} fill="#86868b" fontSize="9" letterSpacing="0.04em">
                  {node.ooo ? `${roleOf(node.kind)} · AWAY` : roleOf(node.kind)}
                </text>
                <text
                  x={12}
                  y={32}
                  fill="#1d1d1f"
                  fontSize="12.5"
                  fontWeight="600"
                  letterSpacing="-0.02em"
                >
                  {node.label}
                </text>
                <text x={12} y={46} fill="#86868b" fontSize="10">
                  {friendlySubtitle(node.kind, node.subtitle, node.ooo)}
                </text>
              </g>
            );
          })}
        </svg>

        {selected ? (
          <aside className="absolute bottom-12 left-3 right-3 rounded-[12px] border border-black/[0.08] bg-white/95 p-3 shadow-sm backdrop-blur">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-[10px] font-medium uppercase tracking-[0.04em] text-apple-muted">
                  {roleOf(selected.kind)}
                  {selected.ooo ? " · away" : ""}
                </div>
                <div className="text-[14px] font-semibold tracking-[-0.02em] text-apple-ink">
                  {selected.label}
                </div>
              </div>
              <div className="flex shrink-0 gap-1">
                {onAsk ? (
                  <button
                    type="button"
                    onClick={() => onAsk(selected)}
                    className="rounded-[8px] bg-[#007AFF] px-2.5 py-1 text-[12px] font-semibold text-white"
                  >
                    Ask about this
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => setSelectedId(null)}
                  className="rounded-[8px] bg-black/[0.05] px-2 py-1 text-[12px] text-apple-muted"
                >
                  Close
                </button>
              </div>
            </div>
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[12px]">
              {Object.entries(selected.facts || {})
                .filter(([, value]) => value !== null && value !== undefined && value !== "")
                .map(([key, value]) => (
                  <div key={key} className={key === "body" || key === "notes" ? "col-span-2" : ""}>
                    <dt className="text-[10px] uppercase tracking-[0.04em] text-apple-muted">
                      {factLabel(key)}
                    </dt>
                    <dd className="text-apple-ink">{formatFact(key, value)}</dd>
                  </div>
                ))}
            </dl>
          </aside>
        ) : null}
      </div>
      <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center gap-2 text-[10px] text-apple-muted">
        {KIND_FILTER.map((item) => {
          const on = kinds[item.id] !== false;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => toggleKind(item.id)}
              aria-pressed={on}
              className={`inline-flex items-center gap-1 rounded-full px-2 py-1 shadow-sm ${
                on ? "bg-white/90 text-apple-ink" : "bg-white/50 text-apple-muted line-through"
              }`}
            >
              <span
                className="h-2 w-2 rounded-full border border-black/10"
                style={{ background: item.swatch }}
              />
              {item.label}
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setView({ x: 0, y: 0, w: WORLD.w, h: WORLD.h })}
          className="ml-auto rounded-full bg-white/90 px-2 py-1 shadow-sm"
        >
          Reset view
        </button>
      </div>
    </div>
  );
}

function inspectorTitle(node: GraphNode): string {
  const facts = Object.entries(node.facts || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== "")
    .map(([k, v]) => `${factLabel(k)}: ${formatFact(k, v)}`)
    .join(" · ");
  return facts ? `${node.label} — ${facts}` : `${node.label}: ${node.subtitle}`;
}

function factLabel(key: string): string {
  const labels: Record<string, string> = {
    role: "Role",
    department: "Department",
    threshold_usd: "Limit",
    ooo_until: "Away until",
    email: "Email",
    location: "Location",
    category: "Category",
    score: "Fit score",
    soc2: "SOC 2",
    incumbent: "Incumbent",
    sla: "SLA",
    notes: "Notes",
    policy_id: "Policy",
    body: "What it says",
    cost_center: "Cost center",
  };
  return labels[key] || key;
}

function formatFact(key: string, value: string | number | boolean | null | undefined): string {
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (key.endsWith("_usd") && typeof value === "number") return `$${value.toLocaleString()}`;
  return String(value);
}

function friendlySubtitle(kind: string, subtitle: string, ooo: boolean): string {
  if (kind === "Employee") {
    const cleaned = subtitle.replace(" · OOO", "").replace("OOO", "away");
    return cleaned.length > 36 ? `${cleaned.slice(0, 36)}…` : cleaned;
  }
  if (kind === "Vendor") {
    return subtitle.replace("design-tools · score", "fit score");
  }
  if (kind === "Policy") {
    return "Applies to this purchase";
  }
  if (ooo) return `${subtitle} · away`;
  return subtitle.length > 36 ? `${subtitle.slice(0, 36)}…` : subtitle;
}

function RegionLabel({ x, y, text }: { x: number; y: number; text: string }) {
  return (
    <text x={x} y={y} fill="#86868b" fontSize="11" fontWeight="600" letterSpacing="0.04em">
      {text.toUpperCase()}
    </text>
  );
}
