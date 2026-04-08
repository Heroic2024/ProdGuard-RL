from scenarios.easy_db_outage import get_scenario as build_easy
from scenarios.hard_cascade_failure import get_scenario as build_hard
from scenarios.medium_memory_leak import get_scenario as build_medium
from incident_types import ScenarioConfig


def load_scenario(task: str) -> ScenarioConfig:
    normalized = (task or "easy").strip().lower()
    if normalized == "easy":
        return build_easy()
    if normalized == "medium":
        return build_medium()
    if normalized == "hard":
        return build_hard()
    raise ValueError(f"Unsupported task '{task}'. Expected one of: easy, medium, hard.")


def supported_tasks() -> list[str]:
    return ["easy", "medium", "hard"]
