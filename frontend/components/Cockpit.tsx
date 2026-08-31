"use client";

import { RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { asTraceKind, continueCycle, getState, sendChat, type CycleEvent } from "@/lib/api";
import { STAGES, stageCopy } from "@/lib/copy";
import type { GraphView, PipelineFile, StageId } from "@/lib/types";
import type { AssistantTurn, TraceStep } from "@/lib/traces";
import { ChatPane, welcomeItem, type ChatItem } from "./ChatPane";
import { GraphPane } from "./GraphPane";
import { WindowControls, useDesktopShell } from "./WindowControls";

type RunState = "idle" | "running" | "awaiting" | "done" | "error";

type Headline = {
  item: string;
  amount: number;
  vendor: string;
};

export function Cockpit() {
  const [graph, setGraph] = useState<GraphView | null>(null);
  const [files, setFiles] = useState<PipelineFile[]>([]);
  const [activeStage, setActiveStage] = useState<StageId>("01_intake");
  const [gated, setGated] = useState(false);
  const [runState, setRunState] = useState<RunState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [nextStage, setNextStage] = useState<StageId | null>(null);
  const [items, setItems] = useState<ChatItem[]>([welcomeItem()]);
  const [headline, setHeadline] = useState<Headline | null>(null);
  const [provider, setProvider] = useState("mock");
  const [footer, setFooter] = useState("One agent. Five hats. Files pass the baton.");
  const desktop = useDesktopShell();

  useEffect(() => {
    getState()
      .then((state) => {
        setGraph(state.graph);
        setFiles(state.files);
        setProvider(state.health.llm);
      })
      .catch(() => {
        setError("Could not reach the review service. Is it running?");
        setRunState("error");
      });
  }, []);

  const applyHighlight = (ids: string[]) => {
    setGraph((current) =>
      current
        ? {
            ...current,
            highlight: ids,
            nodes: current.nodes.map((n) => ({ ...n, active: ids.includes(n.id) })),
            edges: current.edges.map((e) => ({
              ...e,
              active: ids.includes(e.source) && ids.includes(e.target),
            })),
          }
        : current,
    );
  };

  const applyEvent = (event: CycleEvent) => {
    if (event.stage) {
      setActiveStage(event.stage);
    }
    if (event.highlight) applyHighlight(event.highlight);
    if (event.provider) setProvider(event.provider);
    if (event.request?.item && event.request.amount_usd != null) {
      setHeadline({
        item: event.request.item,
        amount: event.request.amount_usd,
        vendor: event.request.vendor_hint || event.request.item,
      });
    }

    if (event.event === "intent" && event.request) {
      const amount = Number(event.request.amount_usd ?? 0);
      setHeadline({
        item: String(event.request.item || "Purchase"),
        amount,
        vendor: String(event.request.vendor_hint || ""),
      });
    }

    if (event.event === "stage_start") {
      const stage = (event.stage || "01_intake") as AssistantTurn["stage"];
      const id = `asst-${stage}-${event.index ?? Date.now()}`;
      setItems((prev) => [
        ...prev.filter((m) => m.kind !== "pause"),
        {
          id,
          kind: "assistant",
          turn: {
            stage,
            hat: event.hat,
            status: "thinking",
            traces: [],
            thought: "",
            summary: "",
            draft: "",
            provider: event.provider,
          },
        },
      ]);
    }

    if (event.event === "reasoning") {
      const step: TraceStep = {
        kind: asTraceKind(event.kind),
        label: event.label || "Step",
        detail: event.detail || "",
        path: event.path,
        loaded: event.loaded,
        budget: event.budget,
      };
      setItems((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          const item = next[i];
          if (item.kind === "assistant" && item.turn.status === "thinking") {
            next[i] = {
              ...item,
              turn: { ...item.turn, traces: [...item.turn.traces, step] },
            };
            break;
          }
        }
        return next;
      });
    }

    if (event.event === "thought_delta" && (event.content || event.text)) {
      const body = event.content || event.text || "";
      setItems((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          const item = next[i];
          if (item.kind === "assistant" && item.turn.status === "thinking") {
            next[i] = { ...item, turn: { ...item.turn, thought: body } };
            break;
          }
        }
        return next;
      });
    }

    if (event.event === "delta" && (event.content || event.text)) {
      const body = event.content || event.text || "";
      setItems((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          const item = next[i];
          if (item.kind === "assistant" && item.turn.status === "thinking") {
            next[i] = { ...item, turn: { ...item.turn, draft: body } };
            break;
          }
        }
        return next;
      });
    }

    if (event.event === "file_written" && event.stage && event.content) {
      const stage = event.stage;
      setFiles((prev) => prev.map((f) => (f.stage === stage ? { ...f, output: event.content! } : f)));
      setItems((prev) =>
        prev.map((m) =>
          m.kind === "assistant" && m.turn.stage === stage && m.turn.status === "thinking"
            ? {
                ...m,
                turn: {
                  ...m.turn,
                  status: "done",
                  hat: event.hat || m.turn.hat,
                  summary: event.summary || "",
                  draft: event.content || m.turn.draft,
                  thought: m.turn.thought,
                  provider: event.provider || m.turn.provider,
                },
              }
            : m,
        ),
      );
      if (event.json && typeof event.json.spender_approver_name === "string") {
        setFooter(`${event.json.spender_approver_name} can approve.`);
      }
    }

    if (event.event === "answer" && event.content) {
      setItems((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          const item = next[i];
          if (item.kind === "assistant" && item.turn.status === "thinking") {
            next[i] = {
              ...item,
              turn: {
                ...item.turn,
                status: "done",
                hat: event.hat || "Graph lookup",
                summary: event.content || "",
                thought: item.turn.thought || event.content,
              },
            };
            break;
          }
        }
        return next;
      });
    }

    if (event.event === "awaiting_human") {
      setRunState("awaiting");
      if (event.next_stage) setNextStage(event.next_stage);
      const hat = event.hat || (event.stage ? stageCopy(event.stage).title : "this step");
      setItems((prev) => [
        ...prev.filter((m) => m.kind !== "pause"),
        {
          id: `pause-${event.stage}`,
          kind: "pause",
          text: `Paused after ${hat}. The next hat will only see this brief plus its own contract.`,
        },
      ]);
    }
    if (event.event === "cycle_complete") {
      setRunState("done");
      setNextStage(null);
    }
    if (event.event === "ask_complete") {
      setRunState("done");
    }
  };

  const start = async (text: string) => {
    setError(null);
    setRunState("running");
    setNextStage(null);
    setItems((prev) => [...prev, { id: `user-${Date.now()}`, kind: "user", text }]);
    try {
      await sendChat(text, gated, applyEvent);
      setRunState((current) => (current === "awaiting" ? "awaiting" : "done"));
    } catch {
      setError("The review could not finish. Try again.");
      setRunState("error");
    }
  };

  const resume = async () => {
    const idx = STAGES.findIndex((s) => s.id === activeStage);
    const fallback = STAGES[Math.min(idx + 1, STAGES.length - 1)].id;
    const target = nextStage ?? fallback;
    if (idx >= STAGES.length - 1 && !nextStage) {
      setRunState("done");
      return;
    }
    setRunState("running");
    try {
      await continueCycle(target, applyEvent);
      setRunState((current) => (current === "awaiting" ? "awaiting" : "done"));
    } catch {
      setError("Could not continue. Try again.");
      setRunState("error");
    }
  };

  const copy = stageCopy(activeStage);
  const amountLabel = headline
    ? `${headline.item} · $${headline.amount.toLocaleString()}`
    : "Purchase review";

  return (
    <div className={desktop ? "flex h-screen" : "flex h-screen items-stretch justify-center p-3"}>
      <div
        className={
          desktop
            ? "flex h-full w-full flex-col overflow-hidden bg-white"
            : "flex h-full w-full max-w-[1440px] flex-col overflow-hidden rounded-[12px] bg-white/80 shadow-window"
        }
      >
        <header className="material hairline pywebview-drag-region drag-region flex h-[52px] shrink-0 items-center px-4">
          <WindowControls />
          <div className="flex-1 text-center">
            <div className="text-[13px] font-semibold tracking-[-0.02em] text-apple-ink">Northstar</div>
            <div className="text-[11px] text-apple-muted">{amountLabel}</div>
          </div>
          <button
            onClick={() => {
              setItems([welcomeItem()]);
              setRunState("idle");
              setError(null);
              setHeadline(null);
              setFooter("One agent. Five hats. Files pass the baton.");
            }}
            aria-label="New chat"
            className="no-drag rounded-[8px] bg-black/[0.05] p-1.5 text-apple-muted hover:text-apple-ink"
          >
            <RotateCcw size={14} />
          </button>
        </header>

        <div className="flex min-h-0 flex-1">
          <section className="flex min-h-0 min-w-0 flex-[1.15] flex-col border-r border-black/[0.06] bg-white">
            <ChatPane
              items={items}
              running={runState === "running"}
              gated={gated}
              onToggleGate={setGated}
              onSend={start}
              onContinue={resume}
              awaiting={runState === "awaiting"}
            />
          </section>
          <section className="relative flex min-h-0 min-w-0 flex-1 flex-col bg-[#f5f5f7]">
            <div className="flex shrink-0 items-center justify-between px-4 py-2.5">
              <h2 className="text-[13px] font-semibold tracking-[-0.02em]">Who is involved</h2>
              <span className="text-[11px] text-apple-muted">Live graph · {provider}</span>
            </div>
            <div className="relative min-h-0 flex-1">
              <GraphPane
                graph={graph}
                caption={copy.mapCaption}
                onAsk={(node) => {
                  if (runState === "running" || runState === "awaiting") return;
                  start(`Tell me about ${node.label}.`);
                }}
              />
            </div>
          </section>
        </div>

        <footer className="material flex shrink-0 items-center justify-between border-t border-black/[0.06] px-4 py-2 text-[12px] text-apple-muted">
          <span>
            {error
              ? error
              : runState === "running"
                ? `Working as ${copy.title.replace(/\?$/, "")}…`
                : runState === "awaiting"
                  ? "Paused — continue when you’ve read the brief."
                  : runState === "done"
                    ? footer
                    : "One agent. Five hats. Files pass the baton."}
          </span>
          <span>Nothing is purchased until a person signs.</span>
        </footer>
      </div>
    </div>
  );
}
