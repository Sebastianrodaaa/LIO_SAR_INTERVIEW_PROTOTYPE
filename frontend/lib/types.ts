export type StageId =
  | "01_intake"
  | "02_compliance_check"
  | "03_vendor_sourcing"
  | "04_negotiation_strategy"
  | "05_approval_routing";

export type GraphNode = {
  id: string;
  kind: "Employee" | "Department" | "Vendor" | "Policy" | string;
  label: string;
  subtitle: string;
  ooo: boolean;
  x: number;
  y: number;
  active: boolean;
  facts?: Record<string, string | number | boolean | null | undefined>;
};

export type GraphEdge = {
  source: string;
  target: string;
  kind: string;
  active: boolean;
};

export type GraphView = {
  backend: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  highlight: string[];
};

export type ContextBudget = {
  layer_0_2: number;
  layer_3: number;
  layer_4: number;
  retrieval: number;
  total: number;
  monolithic_estimate: number;
};

export type PipelineFile = {
  stage: StageId;
  contract: string;
  output: string;
  path: string;
};

export type Health = {
  ok: boolean;
  graph: string;
  llm: string;
  stages: string[];
};
