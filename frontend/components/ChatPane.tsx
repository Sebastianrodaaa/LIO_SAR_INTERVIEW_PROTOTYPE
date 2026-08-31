"use client";

import { ArrowUp, LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { SUGGESTIONS, WELCOME } from "@/lib/traces";
import type { AssistantTurn } from "@/lib/traces";
import { ReasoningTrace } from "./ReasoningTrace";

export type ChatItem =
  | { id: string; kind: "welcome"; text: string }
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "assistant"; turn: AssistantTurn }
  | { id: string; kind: "pause"; text: string }
  | { id: string; kind: "closing"; text: string };

export function ChatPane({
  items,
  running,
  gated,
  onToggleGate,
  onSend,
  onContinue,
  awaiting,
}: {
  items: ChatItem[];
  running: boolean;
  gated: boolean;
  onToggleGate: (value: boolean) => void;
  onSend: (text: string) => void;
  onContinue: () => void;
  awaiting: boolean;
}) {
  const [draft, setDraft] = useState("");
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const live = el.querySelector("[data-live-trace]");
    if (live) {
      live.scrollIntoView({ block: "end", behavior: "smooth" });
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [items, awaiting, running]);

  const send = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || running || awaiting) return;
    onSend(trimmed);
    setDraft("");
  };

  const started = items.some((item) => item.kind === "user");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scroller} className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {items.map((item) => {
          if (item.kind === "welcome") {
            return (
              <div
                key={item.id}
                className="msg-enter mb-4 max-w-[540px] text-[13px] leading-relaxed text-apple-muted"
              >
                {item.text}
              </div>
            );
          }
          if (item.kind === "user") {
            return (
              <div key={item.id} className="msg-enter-right mb-4 flex justify-end">
                <div className="max-w-[85%] rounded-[18px] rounded-br-[6px] bg-[#007AFF] px-3.5 py-2.5 text-[14px] leading-relaxed text-white">
                  {item.text}
                </div>
              </div>
            );
          }
          if (item.kind === "assistant") {
            const { turn } = item;
            const live = turn.status === "thinking";
            const latest = turn.traces[turn.traces.length - 1];
            return (
              <div
                key={item.id}
                className="msg-enter mb-5 max-w-[540px]"
                data-live-trace={live ? "true" : undefined}
              >
                <div className="mb-1.5 text-[11px] font-medium uppercase tracking-[0.04em] text-apple-muted">
                  {turn.hat || "Agent"}
                  {turn.provider ? ` · ${turn.provider}` : ""}
                </div>
                {live ? (
                  <div className="mb-2 rounded-[10px] bg-[#007AFF]/[0.06] px-3 py-2 text-[13px] leading-snug text-apple-ink">
                    <span className="text-[11px] font-medium uppercase tracking-[0.04em] text-[#007AFF]">
                      {turn.thought ? "Thinking" : latest?.label || "GraphRAG"}
                    </span>
                    <div>
                      {turn.thought ||
                        latest?.detail ||
                        "Opening this hat’s CONTEXT.md and the Northstar graph slice…"}
                      {turn.thought ? <span className="thought-caret" aria-hidden /> : null}
                    </div>
                  </div>
                ) : turn.thought ? (
                  <p className="mb-2 text-[13px] leading-relaxed text-apple-ink">{turn.thought}</p>
                ) : null}
                <ReasoningTrace
                  title={live ? "Working" : "Tools"}
                  steps={turn.traces}
                  live={live}
                />
                {live && turn.draft ? (
                  <pre className="mt-2 max-h-[160px] overflow-auto whitespace-pre-wrap rounded-[10px] border border-black/[0.06] bg-[#fafafa] px-3 py-2 font-sans text-[12px] leading-relaxed text-apple-ink">
                    {turn.draft}
                  </pre>
                ) : null}
                {!live && turn.summary ? (
                  <p className="mt-1 text-[13px] leading-relaxed text-apple-ink">{turn.summary}</p>
                ) : null}
                {!live && turn.draft ? (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-[12px] text-apple-muted">
                      Brief written to output.md
                    </summary>
                    <pre className="mt-1.5 whitespace-pre-wrap font-sans text-[12px] leading-relaxed text-apple-ink">
                      {turn.draft}
                    </pre>
                  </details>
                ) : null}
              </div>
            );
          }
          if (item.kind === "pause") {
            return (
              <div
                key={item.id}
                className="msg-enter mb-4 rounded-[12px] border border-black/[0.06] bg-white px-3 py-2.5 text-[13px] text-apple-muted"
              >
                {item.text}
                <button
                  type="button"
                  onClick={onContinue}
                  className="ml-2 inline-flex items-center rounded-[8px] bg-[#007AFF] px-2.5 py-1 text-[12px] font-semibold text-white"
                >
                  Continue
                </button>
              </div>
            );
          }
          return (
            <div key={item.id} className="msg-enter mb-4 max-w-[540px] text-[13px] leading-relaxed text-apple-ink">
              {item.text}
            </div>
          );
        })}
      </div>

      <div className="shrink-0 border-t border-black/[0.06] bg-white/80 px-4 py-3">
        {items.length <= 1 && !running ? (
          <div className="mb-2 flex flex-col gap-1.5">
            {SUGGESTIONS.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => send(prompt)}
                className="max-w-full truncate rounded-full border border-black/[0.08] bg-white px-3 py-1.5 text-left text-[12px] text-apple-ink shadow-sm hover:bg-[#f5f5f7]"
              >
                {prompt}
              </button>
            ))}
          </div>
        ) : null}
        <form
          className="flex items-end gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(draft);
          }}
        >
          <label className="sr-only" htmlFor="chat-input">
            Message
          </label>
          <textarea
            id="chat-input"
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(draft);
              }
            }}
            placeholder={started ? "Ask why, change the amount, or name another vendor…" : "What do you need to buy?"}
            disabled={running || awaiting}
            className="min-h-[44px] flex-1 resize-none rounded-[12px] border border-black/[0.08] bg-[#f5f5f7] px-3 py-2.5 text-[14px] text-apple-ink outline-none placeholder:text-apple-muted focus:border-[#007AFF]/40"
          />
          <button
            type="submit"
            disabled={running || awaiting || !draft.trim()}
            aria-label="Send"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#007AFF] text-white disabled:opacity-40"
          >
            {running ? <LoaderCircle size={16} className="animate-spin" /> : <ArrowUp size={16} />}
          </button>
        </form>
        <label className="mt-2 flex items-center gap-2 text-[11px] text-apple-muted">
          <input
            type="checkbox"
            checked={gated}
            onChange={(e) => onToggleGate(e.target.checked)}
            className="accent-[#007AFF]"
          />
          Pause after each hat so you can read the brief
        </label>
      </div>
    </div>
  );
}

export const welcomeItem = (): ChatItem => ({
  id: "welcome",
  kind: "welcome",
  text: WELCOME,
});
