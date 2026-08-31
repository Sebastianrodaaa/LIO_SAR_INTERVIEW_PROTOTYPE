import type { GraphView, Health, PipelineFile, StageId } from "./types";
import type { TraceKind } from "./traces";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function getHealth(): Promise<Health> {
  const res = await fetch(`${API}/health`);
  if (!res.ok) throw new Error("backend offline");
  return res.json();
}

export async function getState(): Promise<{
  health: Health;
  graph: GraphView;
  files: PipelineFile[];
  last_request?: Record<string, unknown>;
}> {
  const res = await fetch(`${API}/state`);
  if (!res.ok) throw new Error("state failed");
  const data = await res.json();
  return {
    health: data.health,
    graph: data.graph,
    files: data.files,
    last_request: data.last_request,
  };
}

export type CycleEvent = {
  event: string;
  stage?: StageId;
  next_stage?: StageId;
  index?: number;
  text?: string;
  content?: string;
  summary?: string;
  highlight?: string[];
  retrieval_query?: string;
  hat?: string;
  kind?: string;
  label?: string;
  detail?: string;
  path?: string;
  loaded?: string[];
  provider?: string;
  elapsed_ms?: number;
  json?: Record<string, unknown>;
  request?: {
    item?: string;
    amount_usd?: number;
    requester_id?: string;
    vendor_hint?: string;
  };
  budget?: {
    layer_0_2: number;
    layer_3: number;
    layer_4: number;
    retrieval: number;
    total: number;
    monolithic_estimate: number;
  };
};

export function asTraceKind(value: string | undefined): TraceKind {
  const kinds: TraceKind[] = ["role", "read", "tool", "skip", "write", "handoff", "thought", "observe"];
  if (value && (kinds as string[]).includes(value)) return value as TraceKind;
  return "thought";
}

function parseSSEChunk(chunk: string): CycleEvent[] {
  const events: CycleEvent[] = [];
  for (const part of chunk.split("\n\n")) {
    if (!part.trim() || part.startsWith(":")) continue;
    const dataLine = part.split("\n").find((line) => line.startsWith("data: "));
    if (!dataLine) continue;
    events.push(JSON.parse(dataLine.slice(6)));
  }
  return events;
}

function createPacer(onEvent: (event: CycleEvent) => void) {
  const queue: { event: CycleEvent; gap: number }[] = [];
  let timer: ReturnType<typeof setTimeout> | null = null;
  let last = 0;
  let resolveIdle: (() => void) | null = null;
  let idle = Promise.resolve();

  const armIdle = () => {
    idle = new Promise<void>((resolve) => {
      resolveIdle = resolve;
    });
  };

  const pump = () => {
    if (!queue.length) {
      timer = null;
      resolveIdle?.();
      resolveIdle = null;
      return;
    }
    const item = queue[0];
    const wait = Math.max(0, item.gap - (Date.now() - last));
    timer = setTimeout(() => {
      queue.shift();
      last = Date.now();
      onEvent(item.event);
      pump();
    }, wait);
  };

  return {
    push(event: CycleEvent) {
      if (!queue.length && !timer) armIdle();
      queue.push({
        event,
        gap: event.event === "thought_delta" ? 22 : 140,
      });
      if (!timer) pump();
    },
    done() {
      return idle;
    },
  };
}

async function readSSE(
  res: Response,
  onEvent: (event: CycleEvent) => void,
): Promise<void> {
  if (!res.body) throw new Error("no stream");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const pacer = createPacer(onEvent);
  let buffer = "";
  while (true) {
    const value = await reader.read();
    if (value.done) {
      if (buffer.trim()) parseSSEChunk(buffer).forEach((event) => pacer.push(event));
      break;
    }
    buffer += decoder.decode(value.value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    parseSSEChunk(parts.join("\n\n")).forEach((event) => pacer.push(event));
  }
  await pacer.done();
}

export async function sendChat(
  message: string,
  gated: boolean,
  onEvent: (event: CycleEvent) => void,
): Promise<void> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, gated }),
  });
  if (!res.ok) throw new Error("chat failed");
  await readSSE(res, onEvent);
}

export async function continueCycle(
  fromStage: StageId,
  onEvent: (event: CycleEvent) => void,
): Promise<void> {
  const res = await fetch(`${API}/continue-cycle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      from_stage: fromStage,
      request: { gated: true },
    }),
  });
  if (!res.ok) throw new Error("continue failed");
  await readSSE(res, onEvent);
}
