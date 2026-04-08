from server.gpu_mode_environment import GpuModeEnvironment
from models import ActionType, GpuModeAction


def test_reset_returns_clean_state() -> None:
    env = GpuModeEnvironment()
    first = env.reset(episode_id="task:easy")
    assert first.step_count == 0
    assert first.task == "easy"
    assert first.done is False

    env.step(GpuModeAction(action=ActionType.CHECK_LOGS, service="db"))
    second = env.reset(episode_id="task:easy")
    assert second.step_count == 0
    assert second.visible_logs == ["api: ERROR failed to connect to db: connection refused"]


def test_episode_completes_with_score() -> None:
    env = GpuModeEnvironment()
    env.reset(episode_id="task:medium")

    sequence = [
        GpuModeAction(action=ActionType.CHECK_METRICS, service="api"),
        GpuModeAction(action=ActionType.CHECK_LOGS, service="api"),
        GpuModeAction(action=ActionType.SCALE_SERVICE, service="api"),
        GpuModeAction(action=ActionType.ROLLBACK_DEPLOYMENT),
        GpuModeAction(
            action=ActionType.DECLARE_ROOT_CAUSE,
            cause="memory leak in api release",
            confidence=0.9,
        ),
    ]

    obs = None
    for action in sequence:
        obs = env.step(action)
    assert obs is not None
    assert obs.done is True
    assert obs.score is not None
    assert 0.0 <= obs.score <= 1.0


def test_unknown_service_never_crashes() -> None:
    env = GpuModeEnvironment()
    env.reset(episode_id="task:hard")
    obs = env.step(GpuModeAction(action=ActionType.CHECK_LOGS, service="non-existent"))
    assert obs.done is False
    assert obs.last_action_error is not None


def test_max_steps_terminates_episode() -> None:
    env = GpuModeEnvironment()
    obs = env.reset(episode_id="task:easy")
    for _ in range(12):
        if obs.done:
            break
        obs = env.step(GpuModeAction(action=ActionType.CHECK_LOGS, service="db"))
    assert obs.done is True
    assert 0.0 <= float(obs.score or 0.0) <= 1.0
