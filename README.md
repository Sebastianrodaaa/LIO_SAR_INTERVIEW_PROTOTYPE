# Northstar — Single-Agent Procurement Orchestrator

A working prototype of **one model, one loop, five hats** for enterprise software buying.

It exists to make a concrete claim: **single-agent sequential reasoning beats a multi-agent swarm** for work that already has a known order, known tools, and known handoffs. Control flow stays in Python. Each stage loads a small, named slice of context. The filesystem is the state machine. There is no CrewAI, LangChain, or AutoGen graph of agents debating who goes next.

- Method: [Interpretable Context Methodology (ICM)](https://arxiv.org/abs/2603.16021)
- Flow: [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (a *workflow*, not an autonomous swarm)
- UI: chat + live company graph (people, rules, vendors)
- Default LLM: offline mock grounded in the fake company graph (no API key)

Live cockpit: [http://127.0.0.1:3000](http://127.0.0.1:3000) · API: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Why single-agent, not a swarm

Procurement is not an open-ended “who should talk now?” problem. Intake, policy, sourcing, commercial terms, and approval routing already have a sequence. A swarm re-discovers that sequence every run, burns tokens on agent-to-agent chatter, and hides the handoff in private messages.

This prototype does the opposite:

| Swarm (CrewAI / AutoGen / ad-hoc multi-agent) | This repo |
|---|---|
| Several personas, each with its own prompt and often its own hidden history | **One model.** Five contracts (`CONTEXT.md`). Same weights, different load. |
| The model (or a router) decides the next speaker | **Python decides.** `engine/orchestrator.py` is a `for` loop over folders. |
| Everyone’s prompt tends toward “here is the whole problem” | **ICM isolation.** A stage sees only its contract, the previous `output.md`, and a GraphRAG slice. Sister stages never enter the window. |
| Handoffs are chat transcripts | **Handoffs are files.** You can open `workspace/pipeline/02_compliance_check/output.md` and read what the next hat will see. |
| Failures look like “the agents disagreed” | Failures are schema validation, a missing graph edge, or a skipped OOO manager — inspectable. |
| Reasoning is a role-play log | Reasoning is streamed from the **live graph** (this requester, this amount, this vendor) while the hat works. |

The point is not that language models cannot collaborate. It is that **collaboration is the wrong abstraction** when the pipeline is already known. Isolation plus a deterministic loop keeps context small, makes the walk visible, and lets a human pause between hats.

Typical stage budget here is a few thousand tokens, not a 40k+ monolith. That is [lost-in-the-middle](https://arxiv.org/abs/2307.03172) avoided by construction, not by hoping five agents remember what the third one said.

---

## What you will see

**Northstar** is a fake company. Junior SWE **Alex Rivera** (own limit $500) wants software. Manager **Jordan Hale** ($5,000) is out of office. The graph walks `REPORTS_TO` and stops at the first in-office person whose limit covers the amount — **Maya Chen** ($50k) for $15,000, **Helena Voss** ($500k) for $60,000.

The cockpit is a chat on the left and a map of people, rules, and vendors on the right. Click a node to inspect it. Ask about it. Change the amount or the vendor in chat; the walk, the policies, and the written briefs change.

Try:

1. *Alex Rivera needs Figma Enterprise for $15,000 and 120 seats. Jordan is out — who has to sign?* → skip Jordan, Maya signs.
2. *What if that same request were $4,900?* → still Maya (Jordan is away), but the $10k spend gate does not fire.
3. *Buy Penpot instead of Figma.* → Penpot fails SOC 2 Type II; not eligible.

---

## Requirements

- **Python 3.11+**
- **Node.js 20+** (for the Next.js cockpit)
- macOS or Linux. No Docker required.

Neo4j and an OpenAI/Anthropic key are **optional**. The default path is fully offline: NetworkX in memory + a mock LLM that still reads the same GraphRAG slices.

---

## Spin up

```bash
git clone https://github.com/<you>/LIO_SAR_INTERVIEW_PROTOTYPE.git
cd LIO_SAR_INTERVIEW_PROTOTYPE

python3 -m pip install -r requirements.txt
python3 bootstrap.py          # mock company data + ICM folders + graph seed

# terminal 1 — API
make backend                  # http://127.0.0.1:8000

# terminal 2 — cockpit
cd frontend && npm install && npm run dev
# http://127.0.0.1:3000
```

`bootstrap.py` generates `data/` (employees, vendors, policies) and scaffolds `workspace/pipeline/01_intake` … `05_approval_routing`. Re-run it anytime you want a clean factory.

Equivalent without Make:

```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Open the UI, click a suggestion chip (or type a purchase). Watch one agent switch hats: load `CONTEXT.md`, query the graph, type reasoning, write `output.md`, pass the file to the next folder.

Pause after each hat with the checkbox if you want to read the brief before the next contract loads.

### Tests

```bash
make test
```

### Optional: live model

Copy `.env.example` to `.env`:

```bash
LLM_PROVIDER=openai          # or anthropic; default is mock
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

The orchestrator still calls the model **once per folder** and still validates a Pydantic schema. A live provider changes how `output.md` is *written*, not who is in charge of the loop.

### Optional: Neo4j

If `NEO4J_URI` / `NEO4J_PASSWORD` are set and Bolt is up, the same schema is seeded into Neo4j. If not, NetworkX is the graph. The cockpit does not care which backend answered `REPORTS_TO`.

---

## How a cycle runs

Python, not a swarm router:

```
chat message
  → parse intent (run vs ask)
  → for stage in 01_intake … 05_approval_routing:
        read CONTEXT.md
        GraphRAG slice for this stage only
        one structured LLM call
        validate schema
        write output.md / output.json
        stream thought + brief to the cockpit
  → stop (or pause for a human)
```

| Folder | Hat | Graph slice |
|---|---|---|
| `01_intake` | What is being asked? | Requester + manager |
| `02_compliance_check` | Do the rules allow it? | `GOVERNS` policies for amount / category |
| `03_vendor_sourcing` | Is this the right tool? | In-category vendors, SOC 2, tiers |
| `04_negotiation_strategy` | What should we ask for? | Chosen vendor commercial node |
| `05_approval_routing` | Who needs to sign? | `REPORTS_TO` walk, skip OOO |

Each hat’s prompt never includes the other four contracts. The next hat sees a markdown artifact, not a secret chain-of-thought dump.

---

## Layout

```
bootstrap.py              data → folders → graph
main.py                   FastAPI + SSE
engine/orchestrator.py    the loop (this is the architecture)
engine/graphrag.py        stage-scoped retrieval
engine/live_thoughts.py   reasoning text from this request’s graph slice
engine/schemas.py         Pydantic contracts per hat
engine/mock_completions.py  offline, graph-grounded structured output
workspace/pipeline/       01–05  CONTEXT.md + output.md
data/                     Northstar employees, vendors, policies
frontend/                 chat + interactive graph
tests/                    cycle, intent, amount-sensitive routing
```

Do not add LangChain, CrewAI, or AutoGen. One model, one loop.

---

## License

Prototype / demo code. Add a `LICENSE` before treating this as a production dependency.
