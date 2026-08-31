import type { StageId } from "./types";

export type TraceKind = "role" | "read" | "tool" | "skip" | "write" | "handoff" | "thought" | "observe";

export type TraceStep = {
  kind: TraceKind;
  label: string;
  detail: string;
  path?: string;
  loaded?: string[];
  budget?: {
    total: number;
    monolithic_estimate: number;
  };
};

export type AssistantTurn = {
  stage: StageId | "ask";
  hat?: string;
  status: "thinking" | "done" | "paused";
  traces: TraceStep[];
  thought?: string;
  summary: string;
  draft?: string;
  provider?: string;
};

export const WELCOME =
  "Tell me what you need to buy. I’ll walk it through Northstar’s people, rules, and vendors — one hat at a time — and show who has to sign.";

export const SUGGESTIONS = [
  "Alex Rivera needs Figma Enterprise for $15,000 and 120 seats. Jordan is out — who has to sign?",
  "What if that same request were $4,900?",
  "Buy Penpot instead of Figma.",
];
