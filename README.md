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
Meta mode targets `api.meta.ai/v1` and is UNVERIFIED.

## Status

Working end to end in mock mode on a fictional area (Lantern Cove). Runs are held in memory. Design: [docs/AGENT-ARCHITECTURE.md](docs/AGENT-ARCHITECTURE.md).
Planning: [docs/README.md](docs/README.md), gate: [docs/04-FEASIBILITY-TEST.md](docs/04-FEASIBILITY-TEST.md), rules: [AGENTS.md](AGENTS.md).

## NOT tested

Any live Meta call (transcription, structured output, vision); speech accuracy; reading real sketch pixels (mock uses a label list);
real places or boundaries; multiple users; persistence; adversarial prompt-injection input. No accuracy is measured or claimed.
`python spike/check_core.py` remains the original synthetic probe.
