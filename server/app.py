from __future__ import annotations

from threading import Lock

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from env import ProdGuardEnv
from incident_types import AgentAction, IncidentState, StepResult
from scenarios import supported_tasks


class ResetRequest(BaseModel):
    task: str = Field(default="easy")


app = FastAPI(title="IncidentGym", version="1.0.0")
_env = ProdGuardEnv(default_task="easy")
_lock = Lock()


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
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
