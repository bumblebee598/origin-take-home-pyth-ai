import json
import os
import tempfile
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from ingest_paper import prepare_paper
from manim_agent import render_video_plan
from scene_llm import plan_video

app = FastAPI(title="Origin Take Home API")
WORK_DIR = Path(__file__).resolve().parent / "work"
WORK_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/outputs", StaticFiles(directory=WORK_DIR), name="outputs")


class RenderRequest(BaseModel):
    job_id: str


def _job_dir(job_id: str) -> Path:
    return WORK_DIR / "jobs" / job_id


def _status_path(job_id: str) -> Path:
    return _job_dir(job_id) / "status.json"


def _write_status(
    job_id: str,
    status: str,
    message: str,
    details: dict | None = None,
    video_url: str | None = None,
) -> dict[str, Any]:
    payload = {
        "job_id": job_id,
        "status": status,
        "message": message,
        "details": details or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if video_url:
        payload["video_url"] = video_url

    path = _status_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    print(f"[render:{job_id}] {status}: {message}", flush=True)
    return payload


def _read_status(job_id: str) -> dict[str, Any]:
    path = _status_path(job_id)
    if not path.exists():
        return {
            "job_id": job_id,
            "status": "planned",
            "message": "Video plan is ready.",
            "details": {},
        }
    return json.loads(path.read_text())


def _run_render_job(job_id: str) -> None:
    job_dir = _job_dir(job_id)
    plan_path = job_dir / "plan.json"

    try:
        plan_payload = json.loads(plan_path.read_text())

        def progress(message: str, details: dict | None = None) -> None:
            _write_status(job_id, "rendering", message, details)

        _write_status(job_id, "rendering", "Starting video render")
        concurrency = int(os.getenv("RENDER_CONCURRENCY", "2"))
        output_path = asyncio.run(
            render_video_plan(
                plan_payload,
                workroot=str(job_dir / "render"),
                concurrency=concurrency,
                progress=progress,
            )
        )
        relative_output = Path(output_path).resolve().relative_to(WORK_DIR)
        video_url = f"/outputs/{relative_output.as_posix()}"
        _write_status(job_id, "completed", "Render complete", {"video_path": str(output_path)}, video_url)
    except Exception as exc:
        _write_status(job_id, "failed", str(exc))


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/papers/ingest")
async def ingest_paper(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    temp_path = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_path = temp_file.name
            temp_file.write(await file.read())

        extracted_text = await run_in_threadpool(prepare_paper, temp_path)
        video_plan = await run_in_threadpool(plan_video, extracted_text)
        video_plan_payload = video_plan.model_dump()
        job_id = uuid.uuid4().hex
        job_dir = WORK_DIR / "jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "plan.json").write_text(json.dumps(video_plan_payload, indent=2))
        _write_status(job_id, "planned", "Video plan is ready.")

        print(json.dumps(video_plan_payload, indent=2))

        return {
            "job_id": job_id,
            "filename": file.filename or "uploaded-paper.pdf",
            "text": extracted_text,
            "character_count": len(extracted_text),
            "video_plan": video_plan_payload,
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/videos/render")
async def render_video(
    request: RenderRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    job_dir = _job_dir(request.job_id)
    plan_path = job_dir / "plan.json"

    if not plan_path.exists():
        raise HTTPException(status_code=404, detail="No saved video plan found for this job.")

    current_status = _read_status(request.job_id)
    if current_status["status"] in {"rendering", "completed"}:
        return current_status

    _write_status(request.job_id, "queued", "Render queued.")
    background_tasks.add_task(_run_render_job, request.job_id)
    return _read_status(request.job_id)


@app.get("/videos/render/{job_id}")
async def get_render_status(job_id: str) -> dict[str, Any]:
    if not (_job_dir(job_id) / "plan.json").exists():
        raise HTTPException(status_code=404, detail="No saved video plan found for this job.")
    return _read_status(job_id)
