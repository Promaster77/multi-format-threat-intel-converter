"""Tiny sidecar server that always 500s. Used for recording demo failure shots."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.post("/v1/chat/completions")
async def always_fail():
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "demo-only failure", "code": 500}},
    )


@app.get("/")
async def root():
    return {"ok": True, "purpose": "always-500 demo sidecar"}