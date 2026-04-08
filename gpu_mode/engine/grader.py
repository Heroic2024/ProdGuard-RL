from __future__ import annotations

try:
    from ..models import GpuModeAction, ScenarioConfig
except ImportError:
    from models import GpuModeAction, ScenarioConfig


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _is_helpful(action: GpuModeAction, scenario: ScenarioConfig) -> bool:
    for helpful in scenario.helpful_actions:
        if helpful.action != action.action:
            continue
        if helpful.service is None or helpful.service == action.service:
            return True
    return False


def grade_episode(
    scenario: ScenarioConfig,
    action_history: list[GpuModeAction],
    resolution_achieved: bool,
    diagnosis_correct: bool,
    diagnosis_confidence: float,
    step_count: int,
) -> float:
    correctness = 1.0 if (resolution_achieved and diagnosis_correct) else (0.5 if diagnosis_correct else 0.0)
    efficiency = _clamp(1.0 - max(step_count - 1, 0) / float(max(1, scenario.max_steps)))

    helpful_count = sum(1 for action in action_history if _is_helpful(action, scenario))
    action_quality = helpful_count / float(max(1, len(action_history)))

    confidence_term = diagnosis_confidence if diagnosis_correct else (1.0 - diagnosis_confidence) * 0.5

    score = (
        0.55 * correctness
        + 0.25 * efficiency
        + 0.15 * _clamp(action_quality)
        + 0.05 * _clamp(confidence_term)
    )

    if not diagnosis_correct:
        score = min(score, 0.49)

    return round(_clamp(score), 4)
