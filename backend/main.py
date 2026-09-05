"""FastAPI app for SIH-26154 multi-format threat-intel converter."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from ai_client import generate_structured  # used by retry path
from config import settings
from database import SessionLocal, create_tables, get_db
from generators import GENERATORS
from models import Artefact, ArtefactOut, Job, JobCreate, JobOut, Source, SourceCreate

logging.basicConfig(level=settings.LOG_LEVEL)
log = logging.getLogger("main")

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = _CTRL.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text


def artefact_to_out(a: Artefact) -> ArtefactOut:
    content: dict | None = None
    if a.content_json:
        try:
            content = json.loads(a.content_json)
        except Exception:
            content = None
    return ArtefactOut(
        output_type=a.output_type,
        content=content,
        status=a.error_msg and "failed" or "completed",
        error_msg=a.error_msg,
    )


def job_to_out(job: Job, db: Session) -> JobOut:
    artefacts = (
        db.query(Artefact).filter(Artefact.job_id == job.id).all()
    )
    return JobOut(
        id=job.id,
        status=job.status,
        artefacts=[artefact_to_out(a) for a in artefacts],
        created_at=job.created_at,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    log.info("startup ok model=%s", settings.MINIMAX_MODEL)
    yield


app = FastAPI(title="SIH-26154 Converter", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- sources -------------------------------------------------------


@app.post("/sources")
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    if not payload.raw_text.strip():
        raise HTTPException(400, "raw_text empty")
    s = Source(
        raw_text=payload.raw_text,
        normalized_text=normalize(payload.raw_text),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"source_id": s.id, "length": len(s.normalized_text)}


@app.get("/sources/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        raise HTTPException(404, "source not found")
    return {"id": s.id, "raw_text": s.raw_text, "normalized_text": s.normalized_text}


# ---------- jobs ----------------------------------------------------------


async def _run_one(
    output_type: str, source_text: str, params: dict, model_id: str, force_fail: bool = False
) -> tuple[str, dict, str | None]:
    """Run one generator. Returns (output_type, content_dict, error_msg).

    If `force_fail` is True, temporarily redirects the request to the
    always-500 sidecar so demo recordings can show the retry path.
    """
    if force_fail and settings.MINIMAX_API_KEY:
        saved_url = settings.MINIMAX_API_URL
        settings.MINIMAX_API_URL = "http://localhost:9000/v1/chat/completions"
        try:
            return await _run_one(output_type, source_text, params, model_id, force_fail=False)
        finally:
            settings.MINIMAX_API_URL = saved_url

    gen = GENERATORS.get(output_type)
    if not gen:
        return output_type, {}, f"unknown_output_type:{output_type}"
    try:
        result: dict = await gen(source_text, params)
        if isinstance(result, dict) and result.get("error"):
            return output_type, {}, f"{result.get('error')}|raw={result.get('raw', '')[:200]}"
        # Hard enforcement: clamp tweet lengths so they always fit in 270 chars
        # regardless of how chatty the model is. Truncate at word boundary.
        if output_type == "twitter" and isinstance(result, dict):
            thread = result.get("thread")
            if isinstance(thread, list):
                for t in thread:
                    if isinstance(t, dict) and isinstance(t.get("tweet"), str) and len(t["tweet"]) > 270:
                        t["tweet"] = _truncate_at_word(t["tweet"], 267)
        return output_type, result, None
    except Exception as e:  # noqa: BLE001
        return output_type, {}, f"{type(e).__name__}:{e}"


def _truncate_at_word(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > limit - 30:
        cut = cut[:sp]
    return cut.rstrip(",;:. ") + "..."


def _coerce_visual(content: dict) -> dict:
    """Some LLMs use 'description' where our schema expects 'visual'. Bridge that."""
    if not isinstance(content, dict):
        return content
    scenes = content.get("scenes")
    if isinstance(scenes, list):
        for s in scenes:
            if isinstance(s, dict) and not s.get("visual") and s.get("description"):
                s["visual"] = s["description"]
    return content


async def _run_job(
    job_id: str,
    source_text: str,
    output_types: list[str],
    params: dict,
    force_fail: list[str] | None = None,
) -> None:
    """Run all selected generators in parallel; persist artefacts; set job status."""
    force_fail = set(force_fail or [])
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return
        job.status = "running"
        db.commit()

        results = await asyncio.gather(
            *[
                _run_one(
                    t, source_text, params, settings.MINIMAX_MODEL,
                    force_fail=(t in force_fail),
                )
                for t in output_types
            ]
        )

        ok = 0
        for output_type, content, err in results:
            if not err:
                content = _coerce_visual(content)
            a = Artefact(
                job_id=job_id,
                output_type=output_type,
                content_json=json.dumps(content) if not err else None,
                raw_output=(content if err else None) and json.dumps(content) or "",
                error_msg=err,
                model_id=settings.MINIMAX_MODEL,
            )
            if err:
                a.raw_output = json.dumps({"raw": (err or "")[:500]})
                a.content_json = None
            db.add(a)
            if not err:
                ok += 1

        job.completed_at = datetime.utcnow()
        if ok == len(output_types):
            job.status = "completed"
        elif ok == 0:
            job.status = "failed"
        else:
            job.status = "partial_failure"
        db.commit()
        log.info("job done id=%s status=%s ok=%d/%d", job_id, job.status, ok, len(output_types))
    finally:
        db.close()


@app.post("/jobs")
async def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    src = db.query(Source).filter(Source.id == payload.source_id).first()
    if not src:
        raise HTTPException(404, "source not found")

    unknown = [t for t in payload.output_types if t not in GENERATORS]
    if unknown:
        raise HTTPException(400, f"unknown output_types: {unknown}")

    params = {
        "tone": payload.tone,
        "audience": payload.audience,
    }
    job = Job(
        source_id=src.id,
        status="pending",
        params_json=json.dumps(params),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    asyncio.create_task(
        _run_job(
            job.id, src.normalized_text, payload.output_types, params,
            force_fail=payload.force_failure_for,
        )
    )
    return {"job_id": job.id, "status": job.status}


@app.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "job not found")
    return job_to_out(job, db).model_dump(mode="json")


@app.post("/jobs/{job_id}/retry")
async def retry_failed(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "job not found")
    failed_arts = (
        db.query(Artefact)
        .filter(Artefact.job_id == job_id, Artefact.error_msg.isnot(None))
        .all()
    )
    if not failed_arts:
        return {"retried": 0, "status": job.status}

    src = db.query(Source).filter(Source.id == job.source_id).first()
    params: dict[str, Any] = json.loads(job.params_json or "{}")

    async def redo(art: Artefact) -> None:
        out_type = art.output_type
        gen = GENERATORS.get(out_type)
        result: dict = await gen(src.normalized_text, params) if gen else {"error": "unknown"}
        db2 = SessionLocal()
        try:
            fresh = db2.query(Artefact).filter(Artefact.id == art.id).first()
            if not fresh:
                return
            if isinstance(result, dict) and result.get("error"):
                fresh.error_msg = f"{result.get('error')}"
                fresh.raw_output = json.dumps({"raw": str(result.get("raw"))[:500]})
                fresh.content_json = None
            else:
                fresh.error_msg = None
                fresh.content_json = json.dumps(result)
                fresh.raw_output = None
            db2.commit()
        finally:
            db2.close()

    await asyncio.gather(*[redo(art) for art in failed_arts])

    # Recompute job status.
    db.expire_all()
    arts = db.query(Artefact).filter(Artefact.job_id == job_id).all()
    failed_count = sum(1 for a in arts if a.error_msg)
    if failed_count == 0:
        job.status = "completed"
    elif failed_count == len(arts):
        job.status = "failed"
    else:
        job.status = "partial_failure"
    job.completed_at = datetime.utcnow()
    db.commit()

    return {"retried": len(failed_arts), "status": job.status}


@app.get("/")
def root():
    return {"app": "SIH-26154", "model": settings.MINIMAX_MODEL, "endpoints": [
        "POST /sources", "GET /sources/{id}", "POST /jobs", "GET /jobs/{id}", "POST /jobs/{id}/retry"
    ]}