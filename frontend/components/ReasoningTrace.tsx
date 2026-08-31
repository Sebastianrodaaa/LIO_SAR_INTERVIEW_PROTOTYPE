"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Ban,
  ChevronRight,
  Circle,
  FileText,
  LoaderCircle,
  Pencil,
  Search,
  UserRound,
} from "lucide-react";

import type { TraceKind, TraceStep } from "@/lib/traces";
import { NumberTicker } from "./motion";

const ICONS: Record<TraceKind, typeof Search> = {
  role: UserRound,
  read: FileText,
  tool: Search,
  skip: Ban,
  write: Pencil,
  handoff: ArrowRight,
  thought: Circle,
  observe: Search,
};

export function ReasoningTrace({
  title,
  steps,
  open: openProp,
  live,
}: {
  title: string;
  steps: TraceStep[];
  open?: boolean;
  live?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const listRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    if (live) setOpen(true);
    else if (openProp !== undefined) setOpen(openProp);
  }, [openProp, live]);

  useEffect(() => {
    if (!live || !listRef.current) return;
    const last = listRef.current.lastElementChild;
    last?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [steps.length, live]);

  return (
    <div className="mb-2 overflow-hidden rounded-[10px] border border-black/[0.06] bg-[#fafafa]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        aria-expanded={open}
      >
        <ChevronRight
          size={14}
          className={`shrink-0 text-apple-muted transition-transform duration-200 ${open ? "rotate-90" : ""}`}
        />
        {live ? (
          <LoaderCircle size={13} className="shrink-0 animate-spin text-[#007AFF]" />
        ) : (
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-[#007AFF]" />
        )}
        <span className="text-[12px] font-medium tracking-[-0.01em] text-apple-ink">{title}</span>
        <span className="ml-auto text-[11px] text-apple-muted">
          {live ? "Running" : `${steps.length} steps`}
        </span>
      </button>
      {open ? (
        <ol ref={listRef} className="max-h-[240px] overflow-auto border-t border-black/[0.05] px-3 py-2">
          {steps.map((step, i) => {
            const Icon = ICONS[step.kind] ?? Circle;
            const isLatest = live && i === steps.length - 1;
            const compact = step.kind === "thought" || step.kind === "observe";
            return (
              <li key={`${step.kind}-${step.label}-${i}`} className={`flex gap-2 py-1.5 ${isLatest ? "trace-step-in" : ""}`}>
                <Icon size={12} className="mt-0.5 shrink-0 text-apple-muted" />
                <div className="min-w-0">
                  {compact ? (
                    <>
                      <div className="text-[10px] font-medium uppercase tracking-[0.04em] text-apple-muted">
                        {step.label}
                      </div>
                      <div className="text-[12px] leading-snug text-apple-ink">{step.detail}</div>
                    </>
                  ) : (
                    <>
                      <div className="text-[12px] font-medium text-apple-ink">{step.label}</div>
                      <div className="text-[11px] leading-snug text-apple-muted">{step.detail}</div>
                    </>
                  )}
                  {step.path ? (
                    <div className="mt-0.5 font-mono text-[10px] text-[#86868b]">{step.path}</div>
                  ) : null}
                  {step.budget ? (
                    <div className="mt-0.5 text-[10px] text-[#86868b]">
                      <NumberTicker value={step.budget.total} /> tokens this hat
                      {" · "}
                      <NumberTicker value={step.budget.monolithic_estimate} /> if it were one prompt
                    </div>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ol>
      ) : null}
    </div>
  );
}
