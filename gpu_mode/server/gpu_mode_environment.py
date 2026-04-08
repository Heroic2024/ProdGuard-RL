# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Production RL environment for incident response in DevOps scenarios."""

from __future__ import annotations

import os
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

try:
    from ..engine import grade_episode
    from ..models import ActionType, GpuModeAction, GpuModeObservation, ScenarioConfig, ServiceMetrics
except ImportError:
    from engine import grade_episode
    from models import ActionType, GpuModeAction, GpuModeObservation, ScenarioConfig, ServiceMetrics

try:
    from scenarios import load_scenario, supported_tasks
except ModuleNotFoundError:
    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.append(str(_repo_root))
    from scenarios import load_scenario, supported_tasks


@dataclass
class EpisodeRuntime:
    scenario: ScenarioConfig
    observation: GpuModeObservation
    action_history: list[GpuModeAction]
    remediations_completed: set[str]
    revealed_log_index: dict[str, int]
    diagnosis_correct: bool
    diagnosis_confidence: float
    resolved: bool
    done: bool


class GpuModeEnvironment(Environment):
    """Multi-task incident response environment with deterministic scoring."""

    # Enable concurrent WebSocket sessions.
    # Set to True if your environment isolates state between instances.
    # When True, multiple WebSocket clients can connect simultaneously, each
    # getting their own environment instance (when using factory mode in app.py).
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self):
        """Initialize runtime and optional fixed task from env var."""
        self._state = State(episode_id=str(uuid4()), step_count=0)
        self._reset_count = 0
        self._pending_task = os.getenv("GPU_MODE_TASK", "").strip().lower() or None
        self._runtime: EpisodeRuntime | None = None

    def _resolve_task(self, episode_id: str | None) -> str:
        if self._pending_task in supported_tasks():
            return self._pending_task

        if episode_id and episode_id.startswith("task:"):
            candidate = episode_id.split(":", 1)[1].strip().lower()
            if candidate in supported_tasks():
                return candidate

        tasks = supported_tasks()
        return tasks[self._reset_count % len(tasks)]

    @staticmethod
    def _key(action: ActionType, service: str | None) -> str:
        return f"{action.value}:{service or '*'}"

    @staticmethod
    def _normalize(text: str | None) -> str:
        return (text or "").strip().lower()

    @staticmethod
    def _normalize_metric(metric: object) -> ServiceMetrics:
        if isinstance(metric, ServiceMetrics):
            return deepcopy(metric)
        if hasattr(metric, "model_dump"):
            return ServiceMetrics.model_validate(metric.model_dump())
        return ServiceMetrics.model_validate(metric)

    def _build_observation(self, scenario: ScenarioConfig) -> GpuModeObservation:
        return GpuModeObservation(
            alert=scenario.alert,
            visible_logs=list(scenario.initial_visible_logs),
            visible_metrics={
                service: self._normalize_metric(scenario.metrics[service])
                for service in scenario.initial_visible_services
                if service in scenario.metrics
            },
            services=list(scenario.services),
            step_count=0,
            task=scenario.id,
            done=False,
            reward=0.0,
            resolved=False,
            score=None,
            metadata={"scenario": scenario.name, "difficulty": scenario.difficulty},
        )

    def _all_remediations_done(self, runtime: EpisodeRuntime) -> bool:
        for req in runtime.scenario.required_actions:
            if req.action == ActionType.DECLARE_ROOT_CAUSE:
                continue
            if self._key(req.action, req.service) not in runtime.remediations_completed:
                return False
        return True

    def _is_helpful(self, runtime: EpisodeRuntime, action: GpuModeAction) -> bool:
        for helpful in runtime.scenario.helpful_actions:
            if helpful.action != action.action:
                continue
            if helpful.service is None or helpful.service == action.service:
                return True
        return False

    def _mark_requirement(self, runtime: EpisodeRuntime, action: GpuModeAction) -> None:
        for req in runtime.scenario.required_actions:
            if req.action != action.action:
                continue
            if req.service is not None and req.service != action.service:
                continue
            runtime.remediations_completed.add(self._key(req.action, req.service))

    def _reveal_log(self, runtime: EpisodeRuntime, service: str) -> bool:
        hidden_logs = runtime.scenario.hidden_logs.get(service, [])
        idx = runtime.revealed_log_index.get(service, 0)
        if idx >= len(hidden_logs):
            return False
        runtime.revealed_log_index[service] = idx + 1
        runtime.observation.visible_logs.append(hidden_logs[idx])
        return True

    def _finalize_if_done(self, runtime: EpisodeRuntime) -> None:
        if not runtime.done:
            return
        score = grade_episode(
            scenario=runtime.scenario,
            action_history=runtime.action_history,
            resolution_achieved=runtime.resolved,
            diagnosis_correct=runtime.diagnosis_correct,
            diagnosis_confidence=runtime.diagnosis_confidence,
            step_count=runtime.observation.step_count,
        )
        runtime.observation.score = score
        runtime.observation.done = True
        runtime.observation.metadata = {
            **(runtime.observation.metadata or {}),
            "resolved": runtime.resolved,
            "score": score,
        }

    def reset(self, seed: int | None = None, episode_id: str | None = None, **kwargs) -> GpuModeObservation:
        """
        Reset the environment.

        Returns:
            GpuModeObservation with a ready message
        """
        requested_task = kwargs.get("task") if isinstance(kwargs, dict) else None
        task = (requested_task or self._resolve_task(episode_id)).strip().lower()
        scenario = load_scenario(task)

        resolved_episode_id = episode_id or str(uuid4())
        self._state = State(episode_id=resolved_episode_id, step_count=0)
        self._reset_count += 1

        observation = self._build_observation(scenario)
        self._runtime = EpisodeRuntime(
            scenario=scenario,
            observation=observation,
            action_history=[],
            remediations_completed=set(),
            revealed_log_index={service: 0 for service in scenario.services},
            diagnosis_correct=False,
            diagnosis_confidence=0.0,
            resolved=False,
            done=False,
        )
        return deepcopy(observation)

    def step(self, action: GpuModeAction) -> GpuModeObservation:  # type: ignore[override]
        """
        Execute one incident-response action and return updated observation.

        Args:
            action: GpuModeAction with operation and optional parameters

        Returns:
            GpuModeObservation with partially observable state and reward
        """
        if self._runtime is None:
            return self.reset()

        runtime = self._runtime
        obs = runtime.observation

        if runtime.done:
            obs.done = True
            obs.reward = 0.0
            return deepcopy(obs)

        if action.action == ActionType.SELECT_TASK:
            candidate = (action.task or "").strip().lower()
            if candidate in supported_tasks():
                self._pending_task = candidate
                obs.last_action_error = None
                obs.metadata = {**(obs.metadata or {}), "next_task": candidate}
            else:
                obs.last_action_error = f"Unsupported task '{action.task}'"
            obs.reward = -0.1
            return deepcopy(obs)

        self._state.step_count += 1
        obs.step_count = self._state.step_count

        reward = -1.0
        obs.last_action_error = None

        try:
            if action.action in {
                ActionType.CHECK_LOGS,
                ActionType.CHECK_METRICS,
                ActionType.RESTART_SERVICE,
                ActionType.SCALE_SERVICE,
            } and action.service not in runtime.scenario.services:
                obs.last_action_error = f"Unknown service '{action.service}'"
                reward -= 1.0
            elif action.action == ActionType.CHECK_LOGS:
                reward += 1.2 if self._reveal_log(runtime, action.service or "") else 0.2
            elif action.action == ActionType.CHECK_METRICS:
                assert action.service is not None
                if action.service in runtime.scenario.metrics:
                    first_time = action.service not in obs.visible_metrics
                    obs.visible_metrics[action.service] = self._normalize_metric(runtime.scenario.metrics[action.service])
                    reward += 1.0 if first_time else 0.2
                else:
                    reward -= 0.8
            elif action.action == ActionType.RESTART_SERVICE:
                assert action.service is not None
                self._mark_requirement(runtime, action)
                if action.service in obs.visible_metrics:
                    m = obs.visible_metrics[action.service]
                    m.error_rate = max(0.0, m.error_rate * 0.6)
                    m.latency_ms = max(1.0, m.latency_ms * 0.7)
                reward += 2.0 if self._is_helpful(runtime, action) else -0.6
            elif action.action == ActionType.SCALE_SERVICE:
                assert action.service is not None
                self._mark_requirement(runtime, action)
                if action.service in obs.visible_metrics:
                    m = obs.visible_metrics[action.service]
                    m.cpu_pct = max(0.0, m.cpu_pct * 0.8)
                    m.memory_pct = max(0.0, m.memory_pct * 0.9)
                    m.latency_ms = max(1.0, m.latency_ms * 0.85)
                reward += 1.8 if self._is_helpful(runtime, action) else -0.5
            elif action.action == ActionType.ROLLBACK_DEPLOYMENT:
                self._mark_requirement(runtime, action)
                reward += 2.5 if self._is_helpful(runtime, action) else -0.7
            elif action.action == ActionType.DECLARE_ROOT_CAUSE:
                normalized = self._normalize(action.cause)
                aliases = {self._normalize(runtime.scenario.root_cause)}
                aliases.update(self._normalize(a) for a in runtime.scenario.root_cause_aliases)
                runtime.diagnosis_confidence = float(action.confidence or 0.0)
                if normalized in aliases:
                    runtime.diagnosis_correct = True
                    self._mark_requirement(runtime, action)
                    reward += 4.0 + 4.0 * runtime.diagnosis_confidence
                    if self._all_remediations_done(runtime):
                        runtime.resolved = True
                        runtime.done = True
                        reward += runtime.scenario.resolution_bonus
                else:
                    runtime.diagnosis_correct = False
                    reward -= runtime.scenario.wrong_diagnosis_penalty + 2.0 * runtime.diagnosis_confidence
            else:
                reward -= 0.5

            if self._is_helpful(runtime, action):
                reward += 0.6

        except Exception as exc:
            reward -= 3.0
            obs.last_action_error = f"Action handling fallback: {exc}"

        runtime.action_history.append(action)
        obs.resolved = runtime.resolved
        obs.reward = round(reward, 3)

        if obs.step_count >= runtime.scenario.max_steps:
            runtime.done = True

        obs.done = runtime.done
        self._finalize_if_done(runtime)

        return deepcopy(obs)

    @property
    def state(self) -> State:
        """
        Get the current environment state.

        Returns:
            Current State with episode_id and step_count
        """
        return self._state
