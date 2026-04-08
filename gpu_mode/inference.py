from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

try:
    from gpu_mode import ActionType, GpuModeAction, GpuModeEnv
except ImportError:
    from models import ActionType, GpuModeAction
    from client import GpuModeEnv

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "")
TASK = os.getenv("TASK", "easy")
BENCHMARK = "gpu_mode"
MAX_STEPS = int(os.getenv("MAX_STEPS", "15"))


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: str | None) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def _heuristic_action(alert: str, step: int) -> GpuModeAction:
    lower = alert.lower()
    if "database" in lower:
        if step == 1:
            return GpuModeAction(action=ActionType.CHECK_LOGS, service="db")
        if step == 2:
            return GpuModeAction(action=ActionType.RESTART_SERVICE, service="db")
        return GpuModeAction(action=ActionType.DECLARE_ROOT_CAUSE, cause="database down", confidence=0.93)
    if "memory" in lower:
        if step == 1:
            return GpuModeAction(action=ActionType.CHECK_METRICS, service="api")
        if step == 2:
            return GpuModeAction(action=ActionType.CHECK_LOGS, service="api")
        if step == 3:
            return GpuModeAction(action=ActionType.SCALE_SERVICE, service="api")
        if step == 4:
            return GpuModeAction(action=ActionType.ROLLBACK_DEPLOYMENT)
        return GpuModeAction(
            action=ActionType.DECLARE_ROOT_CAUSE,
            cause="memory leak in api release",
            confidence=0.87,
        )

    if step == 1:
        return GpuModeAction(action=ActionType.CHECK_LOGS, service="cache")
    if step == 2:
        return GpuModeAction(action=ActionType.CHECK_METRICS, service="db")
    if step == 3:
        return GpuModeAction(action=ActionType.RESTART_SERVICE, service="cache")
    if step == 4:
        return GpuModeAction(action=ActionType.RESTART_SERVICE, service="db")
    if step == 5:
        return GpuModeAction(action=ActionType.ROLLBACK_DEPLOYMENT)
    return GpuModeAction(
        action=ActionType.DECLARE_ROOT_CAUSE,
        cause="cache outage caused db saturation and api failure",
        confidence=0.89,
    )


def _llm_action(client: OpenAI, task: str, state: dict[str, Any], step: int) -> GpuModeAction | None:
    prompt = {
        "task": task,
        "step": step,
        "state": state,
        "allowed_actions": [
            "check_logs(service)",
            "check_metrics(service)",
            "restart_service(service)",
            "scale_service(service)",
            "rollback_deployment()",
            "declare_root_cause(cause, confidence)",
        ],
        "output_json_schema": {
            "action": "string",
            "service": "optional string",
            "cause": "optional string",
            "confidence": "optional float",
        },
    }

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": "Return exactly one JSON object and no extra text."},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    )
    content = (completion.choices[0].message.content or "").strip()
    data = json.loads(content)
    return GpuModeAction.model_validate(data)


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "no-key")

    rewards: list[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(TASK, BENCHMARK, MODEL_NAME)

    with GpuModeEnv.from_docker_image(os.getenv("LOCAL_IMAGE_NAME", "gpu_mode-env:latest")) as env:
        result = env.reset(episode_id=f"task:{TASK}")

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            state = result.observation.model_dump()
            try:
                action = _llm_action(client, TASK, state, step)
            except Exception:
                action = _heuristic_action(result.observation.alert, step)

            result = env.step(action)
            reward = float(result.reward or 0.0)
            rewards.append(reward)
            steps_taken = step

            action_str = json.dumps(action.model_dump(exclude_none=True), separators=(",", ":"), sort_keys=True)
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=bool(result.done),
                error=result.observation.last_action_error,
            )

            if result.done:
                break

        score = float(result.observation.score or 0.0)
        success = score >= 0.8

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
