from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from engine.grader import grade_episode
from scenarios import load_scenario
from incident_types import ActionType, AgentAction, IncidentState, ScenarioConfig, ServiceMetrics, StepResult


@dataclass
class EpisodeRuntime:
    scenario: ScenarioConfig
    state: IncidentState
    action_history: list[AgentAction]
    remediations_completed: set[str]
    revealed_log_index: dict[str, int]
    diagnosis_correct: bool
    diagnosis_confidence: float
    resolved: bool
    done: bool


class ProdGuardEnv:
    def __init__(self, default_task: str = "easy") -> None:
        self._runtime: EpisodeRuntime | None = None
        self.reset(default_task)

    @staticmethod
    def _metric_copy(metrics: dict[str, ServiceMetrics]) -> dict[str, ServiceMetrics]:
        return {service: deepcopy(metric) for service, metric in metrics.items()}

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        return (value or "").strip().lower()

    def reset(self, task: str = "easy") -> IncidentState:
        scenario = load_scenario(task)
        state = IncidentState(
            alert=scenario.alert,
            visible_logs=list(scenario.initial_visible_logs),
            visible_metrics={
                service: deepcopy(scenario.metrics[service])
                for service in scenario.initial_visible_services
                if service in scenario.metrics
            },
            services=list(scenario.services),
            step_count=0,
        )
        self._runtime = EpisodeRuntime(
            scenario=scenario,
            state=state,
            action_history=[],
            remediations_completed=set(),
            revealed_log_index={service: 0 for service in scenario.services},
            diagnosis_correct=False,
            diagnosis_confidence=0.0,
            resolved=False,
            done=False,
        )
        return self.state()

    def state(self) -> IncidentState:
        if not self._runtime:
            raise RuntimeError("Environment is not initialized")
        return deepcopy(self._runtime.state)

    def _mark_required_action(self, action: AgentAction) -> None:
        runtime = self._runtime
        if not runtime:
            return
        for requirement in runtime.scenario.required_actions:
            if requirement.action != action.action:
                continue
            if requirement.service is not None and requirement.service != action.service:
                continue
            key = f"{requirement.action.value}:{requirement.service or '*'}"
            runtime.remediations_completed.add(key)

    def _all_non_diagnosis_remediations_done(self) -> bool:
        runtime = self._runtime
        if not runtime:
            return False

        for requirement in runtime.scenario.required_actions:
            if requirement.action == ActionType.DECLARE_ROOT_CAUSE:
                continue
            key = f"{requirement.action.value}:{requirement.service or '*'}"
            if key not in runtime.remediations_completed:
                return False
        return True

    def _is_helpful(self, action: AgentAction) -> bool:
        runtime = self._runtime
        if not runtime:
            return False
        for helpful in runtime.scenario.helpful_actions:
            if helpful.action != action.action:
                continue
            if helpful.service is None or helpful.service == action.service:
                return True
        return False

    def _reveal_log(self, service: str) -> bool:
        runtime = self._runtime
        if not runtime:
            return False

        hidden = runtime.scenario.hidden_logs.get(service, [])
        current_index = runtime.revealed_log_index.get(service, 0)
        if current_index >= len(hidden):
            return False

        next_line = hidden[current_index]
        runtime.revealed_log_index[service] = current_index + 1
        runtime.state.visible_logs.append(next_line)
        return True

    def _declare_root_cause(self, action: AgentAction) -> tuple[float, bool]:
        runtime = self._runtime
        if not runtime:
            return -3.0, False

        normalized_cause = self._normalize_text(action.cause)
        aliases = {self._normalize_text(runtime.scenario.root_cause)}
        aliases.update(self._normalize_text(alias) for alias in runtime.scenario.root_cause_aliases)

        runtime.diagnosis_confidence = float(action.confidence or 0.0)

        if normalized_cause in aliases:
            runtime.diagnosis_correct = True
            self._mark_required_action(action)

            diagnosis_reward = 4.0 + 4.0 * runtime.diagnosis_confidence
            if self._all_non_diagnosis_remediations_done():
                runtime.resolved = True
                runtime.done = True
                return diagnosis_reward + runtime.scenario.resolution_bonus, True
            return diagnosis_reward - 2.0, False

        runtime.diagnosis_correct = False
        penalty = runtime.scenario.wrong_diagnosis_penalty + 2.0 * runtime.diagnosis_confidence
        return -penalty, False

    def step(self, action: AgentAction) -> StepResult:
        if not self._runtime:
            self.reset("easy")

        runtime = self._runtime
        assert runtime is not None

        if runtime.done:
            return StepResult(
                state=self.state(),
                reward=0.0,
                done=True,
                info={"message": "Episode already completed."},
            )

        reward = -1.0  # Global step penalty to incentivize shorter solutions.
        info: dict[str, object] = {}

        try:
            if action.action in {
                ActionType.CHECK_LOGS,
                ActionType.CHECK_METRICS,
                ActionType.RESTART_SERVICE,
                ActionType.SCALE_SERVICE,
            }:
                if action.service not in runtime.scenario.services:
                    runtime.state.step_count += 1
                    runtime.action_history.append(action)
                    return StepResult(
                        state=self.state(),
                        reward=reward - 1.0,
                        done=False,
                        info={"warning": f"Unknown service '{action.service}'"},
                    )

            if action.action == ActionType.CHECK_LOGS:
                self._mark_required_action(action)
                revealed = self._reveal_log(action.service or "")
                reward += 1.2 if revealed else 0.2

            elif action.action == ActionType.CHECK_METRICS:
                assert action.service is not None
                self._mark_required_action(action)
                if action.service in runtime.scenario.metrics:
                    first_time = action.service not in runtime.state.visible_metrics
                    runtime.state.visible_metrics[action.service] = deepcopy(runtime.scenario.metrics[action.service])
                    reward += 1.0 if first_time else 0.2
                else:
                    reward -= 0.8

            elif action.action == ActionType.RESTART_SERVICE:
                assert action.service is not None
                self._mark_required_action(action)
                metric = runtime.scenario.metrics.get(action.service)
                if metric and action.service in runtime.state.visible_metrics:
                    current = runtime.state.visible_metrics[action.service]
                    current.error_rate = max(0.0, metric.error_rate * 0.6)
                    current.latency_ms = max(1.0, metric.latency_ms * 0.7)
                reward += 2.0 if self._is_helpful(action) else -0.6

            elif action.action == ActionType.SCALE_SERVICE:
                assert action.service is not None
                self._mark_required_action(action)
                metric = runtime.scenario.metrics.get(action.service)
                if metric and action.service in runtime.state.visible_metrics:
                    current = runtime.state.visible_metrics[action.service]
                    current.cpu_pct = max(0.0, metric.cpu_pct * 0.8)
                    current.memory_pct = max(0.0, metric.memory_pct * 0.9)
                    current.latency_ms = max(1.0, metric.latency_ms * 0.85)
                reward += 1.8 if self._is_helpful(action) else -0.5

            elif action.action == ActionType.ROLLBACK_DEPLOYMENT:
                self._mark_required_action(action)
                reward += 2.5 if self._is_helpful(action) else -0.7

            elif action.action == ActionType.DECLARE_ROOT_CAUSE:
                delta, solved = self._declare_root_cause(action)
                reward += delta
                info["solved"] = solved

            else:
                reward -= 0.5

            if self._is_helpful(action):
                reward += 0.6

        except Exception as exc:  # Defensive safeguard: environment should never crash on a bad action.
            reward -= 3.0
            info["error"] = f"Action handling fallback: {exc}"

        runtime.action_history.append(action)
        runtime.state.step_count += 1

        if runtime.state.step_count >= runtime.scenario.max_steps:
            runtime.done = True

        done = runtime.done
        if done:
            score = grade_episode(
                scenario=runtime.scenario,
                action_history=runtime.action_history,
                resolution_achieved=runtime.resolved,
                diagnosis_correct=runtime.diagnosis_correct,
                diagnosis_confidence=runtime.diagnosis_confidence,
                step_count=runtime.state.step_count,
            )
            info["score"] = score
            info["task"] = runtime.scenario.id
            info["resolved"] = runtime.resolved

        return StepResult(state=self.state(), reward=round(reward, 3), done=done, info=info)
