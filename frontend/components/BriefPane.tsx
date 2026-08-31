"use client";

import type { PipelineFile, StageId } from "@/lib/types";
import { STAGES, stageCopy } from "@/lib/copy";

export function BriefPane({
  files,
  active,
  onSelect,
}: {
  files: PipelineFile[];
  active: StageId;
  onSelect: (id: StageId) => void;
}) {
  const current = files.find((f) => f.stage === active);
  const ready = isReady(current?.output);
  const copy = stageCopy(active);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex gap-1 overflow-x-auto border-b border-black/[0.06] px-2 py-1.5">
        {STAGES.map((stage) => {
          const selected = stage.id === active;
          const done = isReady(files.find((f) => f.stage === stage.id)?.output);
          return (
            <button
              key={stage.id}
              onClick={() => onSelect(stage.id)}
              className={`whitespace-nowrap rounded-md px-2.5 py-1 text-[12px] font-medium ${
                selected ? "bg-black/[0.06] text-apple-ink" : "text-apple-muted hover:text-apple-ink"
              }`}
            >
              <span
                className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${
                  done ? "bg-[#28c840]" : "bg-black/15"
                }`}
              />
              {shortTitle(stage.title)}
            </button>
          );
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {ready ? (
          <article className="max-w-[560px]">{renderMarkdown(stripMeta(current?.output ?? ""))}</article>
        ) : (
          <div className="flex h-full flex-col justify-center">
            <p className="text-[15px] font-semibold tracking-[-0.02em] text-apple-ink">{copy.question}</p>
            <p className="mt-2 max-w-[420px] text-[13px] leading-relaxed text-apple-muted">
              This step has not run yet. Press Review this request and a short brief will appear here
              in plain language.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export function isReady(output?: string): boolean {
  if (!output) return false;
  return !output.includes("awaiting run");
}

function shortTitle(title: string): string {
  const map: Record<string, string> = {
    "What is being asked?": "Request",
    "Do the rules allow it?": "Rules",
    "Is this the right tool?": "Tools",
    "What should we ask for?": "Terms",
    "Who needs to sign?": "Approvers",
  };
  return map[title] ?? title;
}

function stripMeta(text: string): string {
  return cleanProse(
    text
      .replace(/<!--[\s\S]*?-->/g, "")
      .replace(/^\s+/u, "")
      .trim(),
  );
}

function cleanProse(text: string): string {
  return text
    .replace(/`(?:emp|vnd|pol|dept)-[^`]+`/g, "")
    .replace(/\((?:emp|vnd|pol|dept)-[^)]+\)/g, "")
    .replace(/\(\s*\)/g, "")
    .replace(/\bOOO\b/g, "away")
    .replace(/\bdesign-tools\b/g, "design tools")
    .replace(/\*\*Spender approver:\*\*/g, "**Who can sign:**")
    .replace(/\*\*Skipped \(away\):\*\*/g, "**Skipped because they are away:**")
    .replace(/\*\*Ready to route:\*\*/g, "**Ready to send:**")
    .replace(/^# Approval routing packet/m, "# Who needs to sign")
    .replace(/^# Intake packet.*/m, "# What is being asked")
    .replace(/^# Compliance memo/m, "# Do the rules allow it")
    .replace(/^# Sourcing memo.*/m, "# Is this the right tool")
    .replace(/^# Negotiation brief.*/m, "# What should we ask for")
    .replace(/^## Chain/m, "## The approval chain")
    .replace(/^## Functional reviewers \(from compliance\)/m, "## Others who must review")
    .replace(/^## Policy findings/m, "## Which rules apply")
    .replace(/^## Required reviews/m, "## Who else must look")
    .replace(/^## Conditions \(may proceed once met\)/m, "## Before we can buy")
    .replace(/^## Blockers/m, "## What would stop this")
    .replace(/^## Scorecard/m, "## How the options compare")
    .replace(/^## Asks/m, "## What to ask for")
    .replace(/^## Must-have order-form clauses/m, "## Must be in the contract");
}

function renderMarkdown(text: string) {
  const blocks = splitBlocks(text);
  return blocks.map((block, i) => {
    if (block.type === "h1") {
      return (
        <h3 key={i} className="mb-3 text-[20px] font-semibold leading-tight tracking-[-0.03em] text-apple-ink">
          {inline(block.text)}
        </h3>
      );
    }
    if (block.type === "h2") {
      return (
        <h4 key={i} className="mb-2 mt-5 text-[13px] font-semibold tracking-[-0.01em] text-[#007AFF]">
          {inline(block.text)}
        </h4>
      );
    }
    if (block.type === "table") {
      const rows = block.rows.map((row) => row.map(cleanCell));
      const isFieldValue =
        rows[0]?.length === 2 &&
        /field/i.test(rows[0][0] ?? "") &&
        /value/i.test(rows[0][1] ?? "");
      const body = isFieldValue ? rows.slice(1) : rows;
      if (isFieldValue) {
        return (
          <dl key={i} className="mb-4 overflow-hidden rounded-[10px] border border-black/[0.06]">
            {body.map((row, ri) => (
              <div
                key={ri}
                className={`grid grid-cols-[38%_1fr] gap-3 px-3 py-2.5 text-[13px] ${
                  ri % 2 === 0 ? "bg-[#fafafa]" : "bg-white"
                }`}
              >
                <dt className="text-apple-muted">{friendlyField(row[0])}</dt>
                <dd className="m-0 font-medium text-apple-ink">{inline(row[1] ?? "")}</dd>
              </div>
            ))}
          </dl>
        );
      }
      return (
        <div key={i} className="mb-4 overflow-hidden rounded-[10px] border border-black/[0.06]">
          <table className="w-full border-collapse text-[13px]">
            <tbody>
              {body.map((row, ri) => (
                <tr key={ri} className={ri === 0 ? "bg-[#f5f5f7]" : "bg-white"}>
                  {row.map((cell, ci) => {
                    const Tag = ri === 0 ? "th" : "td";
                    const display = ri === 0 ? friendlyField(cell) : cell;
                    return (
                      <Tag
                        key={ci}
                        className={`border-t border-black/[0.05] px-3 py-2 text-left ${
                          ri === 0 ? "font-medium text-apple-muted" : "text-apple-ink"
                        }`}
                      >
                        {inline(display)}
                      </Tag>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }
    if (block.type === "list") {
      return (
        <ul key={i} className="mb-4 list-disc space-y-1.5 pl-5 text-[13px] leading-relaxed text-[#3a3a3c]">
          {block.items.map((item, li) => (
            <li key={li}>{inline(item)}</li>
          ))}
        </ul>
      );
    }
    return (
      <p key={i} className="mb-3 text-[14px] leading-relaxed text-[#3a3a3c]">
        {inline(block.text)}
      </p>
    );
  });
}

function cleanCell(text: string): string {
  const actions: Record<string, string> = {
    requester: "Asked",
    skipped_ooo: "Skipped · away",
    spender_approver: "Can sign",
    informed: "Copied",
    functional_reviewer: "Also reviews",
  };
  const trimmed = text
    .replace(/`(?:emp|vnd|pol|dept)-[^`]+`/g, "")
    .replace(/\((?:emp|vnd|pol|dept)-[^)]+\)/g, "")
    .replace(/\(\s*\)/g, "")
    .replace(/\bOOO\b/g, "away")
    .replace(/\bdesign-tools\b/g, "design tools")
    .replace(/POL-[A-Z]+-\d+\s*/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();
  return actions[trimmed] ?? trimmed;
}

function friendlyField(label: string): string {
  const map: Record<string, string> = {
    Requester: "Asked by",
    Role: "Role",
    Department: "Team",
    "Own threshold": "They can approve up to",
    Manager: "Their manager",
    Item: "What they want",
    "Vendor hint": "Suggested vendor",
    Category: "Type",
    Amount: "Cost",
    Seats: "People using it",
    Urgency: "Urgency",
    "Exceeds own threshold": "Needs a higher-up to sign",
    "Spender approver": "Who can sign",
    "Skipped (away)": "Skipped because they are away",
    "Ready to route": "Ready to send",
    "Risk level": "Risk",
    Primary: "Recommended",
    Alternative: "Backup option",
    Person: "Person",
    Threshold: "Can approve up to",
    Action: "In this request",
    Reason: "Why",
    ID: "Rule",
    Title: "Rule",
    Status: "Result",
    Requirement: "What it asks",
    Vendor: "Software",
    Tier: "Plan",
    Annual: "Yearly cost",
    Score: "Fit",
    Eligible: "Allowed?",
    Rationale: "Why",
  };
  return map[label] ?? label;
}

function inline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-apple-ink">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      const inner = part.slice(1, -1);
      if (/^(emp|vnd|pol|dept)-/.test(inner)) return "";
      return (
        <span key={i} className="text-apple-ink">
          {inner}
        </span>
      );
    }
    return part;
  });
}

type Block =
  | { type: "h1" | "h2" | "p"; text: string }
  | { type: "list"; items: string[] }
  | { type: "table"; rows: string[][] };

function splitBlocks(text: string): Block[] {
  const lines = text.split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push({ type: "h1", text: line.slice(2).trim() });
      i += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push({ type: "h2", text: line.slice(3).trim() });
      i += 1;
      continue;
    }
    if (line.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        const cells = lines[i]
          .split("|")
          .slice(1, -1)
          .map((c) => c.trim());
        if (!cells.every((c) => /^[-:]+$/.test(c))) rows.push(cells);
        i += 1;
      }
      blocks.push({ type: "table", rows });
      continue;
    }
    if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(lines[i].slice(2).trim());
        i += 1;
      }
      blocks.push({ type: "list", items });
      continue;
    }
    blocks.push({ type: "p", text: line.trim() });
    i += 1;
  }
  return blocks;
}
