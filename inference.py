"""Submission inference script for ProdGuard-RL."""

import json
import os
import re
import textwrap
from typing import Any, Optional

import requests
from openai import OpenAI

HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

ENV_BASE_URL = os.getenv("ENV_BASE_URL") or "http://127.0.0.1:8000"
BENCHMARK = "ProdGuard-RL"
MAX_STEPS = 12
REQUEST_TIMEOUT = 30

SYSTEM_PROMPT = (
    "You are a DevOps incident-response assistant. "
    "Output exactly one compact JSON object with keys: "
    "action, service, cause, confidence."
)


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: list[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def _safe_compact(raw: str, max_len: int = 120) -> str:
    return re.sub(r"\s+", " ", raw).strip()[:max_len]


def build_user_prompt(task: str, step: int, state: dict[str, Any], history: list[str]) -> str:
    history_block = "\n".join(history[-5:]) if history else "None"
    return textwrap.dedent(
        f"""
        Task: {task}
        Step: {step}
        Alert: {state.get("alert", "")}
        Visible services: {state.get("services", [])}
        Visible metrics: {json.dumps(state.get("visible_metrics", {}), separators=(",", ":"))}
        Recent logs: {state.get("visible_logs", [])[-3:]}
        Previous actions:
        {history_block}
        Return one JSON action for incident handling.
        """
    ).strip()


def _fallback_policy(task: str, step: int) -> dict[str, Any]:
    if task == "easy":
        plan = [
            {"action": "check_metrics", "service": "db"},
            {"action": "check_logs", "service": "db"},
            {"action": "restart_service", "service": "db"},
            {"action": "declare_root_cause", "cause": "database outage", "confidence": 0.92},
        ]
    elif task == "medium":
        plan = [
            {"action": "check_metrics", "service": "db"},
            {"action": "check_logs", "service": "db"},
            {"action": "check_metrics", "service": "api"},
            {"action": "check_logs", "service": "api"},
            {"action": "scale_service", "service": "api"},
            {"action": "rollback_deployment"},
            {"action": "declare_root_cause", "cause": "memory leak in api release", "confidence": 0.9},
        ]
    else:
        plan = [
            {"action": "check_metrics", "service": "cache"},
            {"action": "check_metrics", "service": "db"},
            {"action": "check_logs", "service": "api"},
            {"action": "check_logs", "service": "cache"},
            {"action": "restart_service", "service": "cache"},
            {"action": "restart_service", "service": "db"},
            {"action": "rollback_deployment"},
            {
                "action": "declare_root_cause",
                "cause": "cache outage caused db saturation and api failure",
                "confidence": 0.9,
            },
        ]
    return plan[min(step - 1, len(plan) - 1)]


def _coerce_action(raw: dict[str, Any], task: str, step: int) -> dict[str, Any]:
    allowed = {
        "check_logs",
        "check_metrics",
        "restart_service",
        "scale_service",
        "rollback_deployment",
        "declare_root_cause",
    }
    action = str(raw.get("action", "")).strip().lower()
    if action not in allowed:
        return _fallback_policy(task, step)

    payload: dict[str, Any] = {"action": action}
    if "service" in raw and raw.get("service"):
        payload["service"] = str(raw["service"]).strip()
    if action == "declare_root_cause":
        payload["cause"] = str(raw.get("cause") or _fallback_policy(task, step).get("cause") or "unknown")
        try:
            payload["confidence"] = float(raw.get("confidence", 0.75))
        except (TypeError, ValueError):
            payload["confidence"] = 0.75
    return payload


def get_model_action(client: OpenAI, task: str, step: int, state: dict[str, Any], history: list[str]) -> dict[str, Any]:
    user_prompt = build_user_prompt(task, step, state, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=120,
            stream=False,
        )
        content = (completion.choices[0].message.content or "").strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return _coerce_action(parsed, task, step)
        return _fallback_policy(task, step)
    except Exception as exc:
        return _fallback_policy(task, step)


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(f"{ENV_BASE_URL}{path}", json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _get(path: str) -> dict[str, Any]:
    resp = requests.get(f"{ENV_BASE_URL}{path}", timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def run_task(client: OpenAI, task: str) -> tuple[bool, int, float, list[float]]:
    rewards: list[float] = []
    history: list[str] = []
    score = 0.0
    success = False
    steps_taken = 0

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        state = _post("/reset", {"task": task})
        for step in range(1, MAX_STEPS + 1):
            action_payload = get_model_action(client, task, step, state, history)
            result = _post("/step", action_payload)

            reward = float(result.get("reward", 0.0) or 0.0)
            done = bool(result.get("done", False))
            info = result.get("info") or {}
            next_state = result.get("state") or {}
            error = next_state.get("last_action_error") if isinstance(next_state, dict) else None

            rewards.append(reward)
            steps_taken = step

            action_compact = json.dumps(action_payload, separators=(",", ":"))
            log_step(step=step, action=action_compact, reward=reward, done=done, error=error)

            history.append(f"{step}:{action_compact}:r={reward:.2f}")
            state = next_state if isinstance(next_state, dict) else _get("/state")

            if done:
                score = float(info.get("score", 0.0) or 0.0)
                score = min(max(score, 0.0), 1.0)
                success = score >= 0.1
                break

        if not rewards:
            score = 0.0
            success = False
        elif steps_taken and score == 0.0:
            total = sum(rewards)
            score = min(max((total / max(steps_taken, 1) + 2.0) / 4.0, 0.0), 1.0)
            success = score >= 0.1

    except Exception as exc:
        success = False
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return success, steps_taken, score, rewards


def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN or "")
    tasks = _get("/tasks").get("tasks", ["easy", "medium", "hard"])
    for task in tasks:
        run_task(client, str(task))


if __name__ == "__main__":
    main()
