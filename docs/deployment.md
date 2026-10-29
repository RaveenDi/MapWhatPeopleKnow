# Deployment

## Docker (recommended)

```bash
docker build -t map-what-people-know .
docker run --rm -p 8000:8000 map-what-people-know
```

Open http://127.0.0.1:8000. With no `MODEL_API_KEY` the app runs in **mock** mode (offline pipeline, canned model replies; never reported as model results).

Compose: `docker compose up --build`. To use Meta models, copy `.env.example` to `.env`, set `MODEL_PROVIDER=meta` and `MODEL_API_KEY`, then start with `docker compose --env-file .env up`.

## Environment

| Variable | Meaning |
|---|---|
| `MODEL_PROVIDER` | `mock` (default) or `meta` |
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
