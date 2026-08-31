# LIO SAR Interview Prototype

Single-agent procurement orchestration. Folders are the architecture.
Method: [ICM](https://arxiv.org/abs/2603.16021). Flow: [Anthropic workflows](https://www.anthropic.com/engineering/building-effective-agents).

## Where to go

| Task | Path |
|---|---|
| Run demo | `python3 bootstrap.py` then `make backend` + `make frontend` |
| Mock enterprise | `mock_data_generator.py` → `data/` |
| ICM stages | `workspace/pipeline/` |
| Graph seed | `graph_seed.py` |
| Orchestrator | `engine/orchestrator.py` |
| API | `main.py` |
| Cockpit | `frontend/` |

Do not introduce LangChain, CrewAI, or AutoGen. One model, one loop.
