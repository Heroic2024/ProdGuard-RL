from __future__ import annotations

from typing import Any


def heuristic_policy(state: dict[str, Any], step_idx: int) -> dict[str, Any]:
    alert = (state.get("alert") or "").lower()

    if "database" in alert:
        if step_idx == 0:
            return {"action": "check_logs", "service": "db"}
        if step_idx == 1:
            return {"action": "restart_service", "service": "db"}
        return {"action": "declare_root_cause", "cause": "database down", "confidence": 0.9}

    if "memory" in alert:
        if step_idx == 0:
            return {"action": "check_metrics", "service": "api"}
        if step_idx == 1:
            return {"action": "check_logs", "service": "api"}
        if step_idx == 2:
            return {"action": "scale_service", "service": "api"}
        if step_idx == 3:
            return {"action": "rollback_deployment"}
        return {"action": "declare_root_cause", "cause": "memory leak in api release", "confidence": 0.85}

    if step_idx == 0:
        return {"action": "check_logs", "service": "cache"}
    if step_idx == 1:
        return {"action": "check_metrics", "service": "db"}
    if step_idx == 2:
        return {"action": "restart_service", "service": "cache"}
    if step_idx == 3:
        return {"action": "restart_service", "service": "db"}
    if step_idx == 4:
        return {"action": "rollback_deployment"}
    return {
        "action": "declare_root_cause",
        "cause": "cache outage caused db saturation and api failure",
        "confidence": 0.88,
    }
