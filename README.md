# Map What People Know

A person's sketch plus spoken explanation become map features and, where anchored, a draft boundary they can inspect.
Contradictions between sketch and speech are surfaced with both sources, never silently merged.

## Quick start (mock mode, no API key)

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.lock.txt      # Windows; use .venv/bin on Linux/macOS
.venv\Scripts\python scripts\make_demo.py               # optional; the server also generates it
.venv\Scripts\python -m uvicorn app.main:app --app-dir apps/api --port 8000
```

Open http://localhost:8000, press "Load built-in demo case". Confirm the proposed anchors to get a draft polygon;
answer the sketch-vs-speech contradiction (footpath east vs west of the school). The red shrine stays unresolved.
Tests: `.venv\Scripts\python -m pytest -q`.

`MODEL_PROVIDER=mock|meta` (default mock unless `MODEL_API_KEY` is set; copy `.env.example` to `.env`).
Meta mode targets `api.meta.ai/v1`; the chat (strict JSON, image), tool-calling and `/asr/transcribe` (WAV only) wire shapes were verified live on 2026-10-30 with synthetic input and are pinned by `apps/api/tests/fixtures/live/`. Answer quality on real sketches and speech is UNVERIFIED. Optional: `META_REASONING_EFFORT=minimal|low|medium|high|xhigh`, `META_MAX_COMPLETION_TOKENS` (default 2048).

## Status

Working end to end in mock mode on a fictional area (Lantern Cove). Runs are held in memory. Design: [docs/architecture/agent-architecture.md](docs/architecture/agent-architecture.md).
Planning: [docs/planning/overview.md](docs/planning/overview.md), gate: [docs/planning/04-FEASIBILITY-TEST.md](docs/planning/04-FEASIBILITY-TEST.md), rules: [AGENTS.md](AGENTS.md).

## NOT tested

Any live Meta call (transcription, structured output, vision); speech accuracy; reading real sketch pixels (mock uses a label list);
real places or boundaries; multiple users; persistence; adversarial prompt-injection input. No accuracy is measured or claimed.
`python evals/probes/check_core.py` remains the original synthetic probe.


## Repository layout

```
apps/api/        FastAPI service (agents, providers, domain logic, tests)
apps/web/        user interface
evals/           evaluation runners, fixtures and feasibility probes (evals/probes)
scripts/         demo data and local tooling
docs/            architecture/, deployment.md, planning/
.claude/skills/  agent-architecture, harness, evaluation, deployment skills
Dockerfile  docker-compose.yml  .github/workflows/ci.yml
```

Deploy: see [docs/deployment.md](docs/deployment.md).
