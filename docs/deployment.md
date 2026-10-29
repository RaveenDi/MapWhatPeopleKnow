# Deployment

## Docker (recommended)

```bash
docker build -t map-what-people-know .
docker run --rm -p 8000:8000 map-what-people-know
```

Open http://127.0.0.1:8000. Unless `MODEL_PROVIDER` is explicitly configured, the app runs in **mock** mode (offline pipeline, canned model replies; never reported as model results).

Compose: `docker compose up --build`. To use Meta models, copy `.env.example` to `.env`, set `MODEL_PROVIDER=meta` and `MODEL_API_KEY`, then start with `docker compose --env-file .env up`.

## Environment

| Variable | Meaning |
|---|---|
| `MODEL_PROVIDER` | `mock` (default), `meta`, or `replay` |
| `MODEL_API_KEY` | Meta Model API key. Never commit it. Server-side only. |

## Limits

- Run **one process** (no `--workers`): the worker is in-process and state is local.
- Data lives in `/app/data`; the compose file mounts a volume there. Add retention and auth before a public host.
- Live Meta endpoint shapes are **UNVERIFIED** until the real-model gate runs. The image has been built and started only where stated in the README status.

## Record and replay

`MODEL_PROVIDER=mock|meta|replay` defaults to mock, even when a key is present.
Meta saves successful request/response pairs as `data/recordings/<sha256>.json`;
replay uses the exact canonical request hash and raises `ReplayMiss` on a miss,
without network access. `RECORDINGS_DIR` overrides the directory. Headers and
credentials are never recorded. Recordings contain input text/images/audio and
model responses: keep this gitignored directory private. Meta shapes remain
**UNVERIFIED**; no live calls were made for this implementation.

## Resolver and budgets

`MODEL_MAX_CALLS` defaults to 24 per run, including extraction, retries, repair
and resumed resolver work. `RESOLVER_MAX_STEPS` defaults to 8 and cannot raise
the hard eight-turn cap. Runs report `partial_call_cap`, `partial_step_cap` or
`unresolved` when work cannot finish. HTTP timeout/429/5xx retries are limited to
two; backoff honors Retry-After up to 30 seconds (larger waits fail unresolved).
Malformed structured output gets one repair attempt. Exact replay misses raise.

Trace JSON remains an array with a final `RunTotals` entry; run JSON includes
`telemetry`, also displayed on the web page. Missing tokens/cost are incomplete.
Prices in `apps/api/app/config.py` are illustrative **UNVERIFIED** USD per million
tokens; replace them with verified prices before using estimates for decisions.
No live endpoint, tool-call shape, or billing behavior has been verified.

Offline paired evaluation: `.venv\Scripts\python.exe evals/run.py --provider mock
--manifest evals/manifest.jsonl --split dev --max-calls 100` (one command).
See `evals/README.md` for schema, scoring, replay and held-out discipline.
