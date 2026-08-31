import type { StageId } from "./types";

export const STAGES: {
  id: StageId;
  title: string;
  question: string;
  doing: string;
  mapCaption: string;
}[] = [
  {
    id: "01_intake",
    title: "What is being asked?",
    question: "Who wants this, and what does it cost?",
    doing: "Reading the request…",
    mapCaption: "Highlighting the person who asked, and the manager they report to.",
  },
  {
    id: "02_compliance_check",
    title: "Do the rules allow it?",
    question: "Which company policies apply to this software purchase?",
    doing: "Checking company rules…",
    mapCaption: "Highlighting the policies that apply — spend limit, security, and legal.",
  },
  {
    id: "03_vendor_sourcing",
    title: "Is this the right tool?",
    question: "Should we stay with this vendor, or is there a better option?",
    doing: "Comparing design tools…",
    mapCaption: "Highlighting design-tool vendors. Only this category — not every product we buy.",
  },
  {
    id: "04_negotiation_strategy",
    title: "What should we ask for?",
    question: "What price, term, and contract terms are reasonable?",
    doing: "Preparing talking points…",
    mapCaption: "Focusing on the recommended vendor and its pricing.",
  },
  {
    id: "05_approval_routing",
    title: "Who needs to sign?",
    question: "Who is away, and whose limit covers this amount?",
    doing: "Finding the right approver…",
    mapCaption: "Walking the reporting line, skipping anyone out of office, until someone’s limit covers the amount.",
  },
];

export function stageCopy(id: StageId) {
  return STAGES.find((s) => s.id === id) ?? STAGES[0];
}
