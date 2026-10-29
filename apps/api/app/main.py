import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

load_dotenv()

from . import demo, pipeline  # noqa: E402
from .providers import provider_name  # noqa: E402

app = FastAPI(title="Map What People Know")
WEB = Path(__file__).resolve().parents[2] / "web" / "index.html"


class AnswerIn(BaseModel):
    contradiction_id: str
    chosen_observation_id: str | None = None
    note: str = ""


class ConfirmIn(BaseModel):
    anchor_ids: list[str]


def _run(rid: str) -> dict:
    r = pipeline.RUNS.get(rid)
    if r is None:
        raise HTTPException(404, "unknown run")
    return r


@app.get("/")
def index():
    return FileResponse(WEB)


@app.get("/api/health")
def health():
    return {"ok": True, "provider": provider_name()}


@app.post("/api/runs")
async def post_run(transcript: str | None = Form(None), area_json: str | None = Form(None),
                   sketch_labels_json: str | None = Form(None), sketch: UploadFile | None = File(None),
                   audio: UploadFile | None = File(None)):
    area = json.loads(area_json) if area_json else demo.AREA
    labels = json.loads(sketch_labels_json) if sketch_labels_json else []
    if not transcript and not audio:
        raise HTTPException(422, "transcript or audio required")
    run = pipeline.create_run(area, transcript, await audio.read() if audio else None,
                              audio.filename if audio else "", await sketch.read() if sketch else None, labels)
    return pipeline.view(run)


@app.post("/api/runs/demo")
def post_demo():
    if not (demo.DEMO_DIR / "sketch.png").exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_demo", demo.DEMO_DIR.parents[1] / "scripts" / "make_demo.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.make()
    d = demo.DEMO_DIR
    run = pipeline.create_run(demo.AREA, (d / "transcript.txt").read_text(encoding="utf-8"), None, "",
                              (d / "sketch.png").read_bytes(), json.loads((d / "sketch_labels.json").read_text()))
    return pipeline.view(run)


@app.get("/api/runs/{rid}")
def get_run(rid: str):
    return pipeline.view(_run(rid))


@app.get("/api/runs/{rid}/trace")
def get_trace(rid: str):
    return [s.model_dump() for s in _run(rid)["trace"]]


@app.get("/api/runs/{rid}/sketch")
def get_sketch(rid: str):
    png = _run(rid)["sketch_png"]
    if not png:
        raise HTTPException(404, "no sketch")
    return Response(png, media_type="image/png")


@app.post("/api/runs/{rid}/answers")
def post_answer(rid: str, body: AnswerIn):
    run = _run(rid)
    try:
        pipeline.answer(run, body.contradiction_id, body.chosen_observation_id, body.note)
    except (KeyError, ValueError) as e:
        raise HTTPException(422, str(e))
    return pipeline.view(run)


@app.post("/api/runs/{rid}/confirm")
def post_confirm(rid: str, body: ConfirmIn):
    run = _run(rid)
    try:
        pipeline.confirm(run, body.anchor_ids)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return pipeline.view(run)


@app.get("/api/runs/{rid}/export")
def export(rid: str):
    return pipeline.export_geojson(_run(rid))
