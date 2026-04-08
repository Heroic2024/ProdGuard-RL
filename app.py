from __future__ import annotations

from pathlib import Path
from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from env import ProdGuardEnv
from incident_types import AgentAction, IncidentState, StepResult
from scenarios import supported_tasks


class ResetRequest(BaseModel):
    task: str = Field(default="easy")


app = FastAPI(title="IncidentGym", version="1.0.0")
_env = ProdGuardEnv(default_task="easy")
_lock = Lock()
_frontend_dir = Path(__file__).parent / "frontend"

if _frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="static")


@app.get("/")
def home() -> FileResponse:
    if not _frontend_dir.exists():
        raise HTTPException(status_code=404, detail="Frontend directory not found")
    return FileResponse(_frontend_dir / "index.html")


@app.get("/web")
@app.get("/web/")
def web_home() -> FileResponse:
    # HF Space UI sometimes probes /web; serve the same landing page.
    return home()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def tasks() -> dict[str, list[str]]:
    return {"tasks": supported_tasks()}


@app.post("/reset", response_model=IncidentState)
def reset(payload: ResetRequest) -> IncidentState:
    task = (payload.task or "easy").strip().lower()
    if task not in set(supported_tasks()):
        raise HTTPException(status_code=400, detail=f"Unsupported task '{payload.task}'")
    with _lock:
        return _env.reset(task)


@app.post("/step", response_model=StepResult)
def step(action: AgentAction) -> StepResult:
    with _lock:
        return _env.step(action)


@app.get("/state", response_model=IncidentState)
def state() -> IncidentState:
    with _lock:
        return _env.state()


def main() -> None:
    uvicorn.run("app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
