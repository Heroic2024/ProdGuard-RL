# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Typed models for the Gpu Mode incident-response RL environment."""

from enum import Enum
from typing import Any

from openenv.core.env_server.types import Action, Observation
from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    CHECK_LOGS = "check_logs"
    CHECK_METRICS = "check_metrics"
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    DECLARE_ROOT_CAUSE = "declare_root_cause"
    SELECT_TASK = "select_task"


class ServiceMetrics(BaseModel):
    cpu_pct: float = Field(ge=0.0, le=100.0)
    memory_pct: float = Field(ge=0.0, le=100.0)
    error_rate: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    rps: float = Field(ge=0.0)


class GpuModeAction(Action):
    """Action schema for production incident response episodes."""

    action: ActionType
    service: str | None = None
    cause: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    task: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "GpuModeAction":
        if self.action in {
            ActionType.CHECK_LOGS,
            ActionType.CHECK_METRICS,
            ActionType.RESTART_SERVICE,
            ActionType.SCALE_SERVICE,
        } and not self.service:
            raise ValueError("service is required for service-scoped actions")

        if self.action == ActionType.DECLARE_ROOT_CAUSE:
            if not self.cause:
                raise ValueError("cause is required for declare_root_cause")
            if self.confidence is None:
                raise ValueError("confidence is required for declare_root_cause")

        if self.action == ActionType.SELECT_TASK and not self.task:
            raise ValueError("task is required for select_task")

        return self


class GpuModeObservation(Observation):
    """Partially observable environment state returned on reset/step."""

    alert: str = ""
    visible_logs: list[str] = Field(default_factory=list)
    visible_metrics: dict[str, ServiceMetrics] = Field(default_factory=dict)
    services: list[str] = Field(default_factory=list)
    step_count: int = Field(default=0, ge=0)
    task: str = "easy"
    resolved: bool = False
    score: float | None = None
    last_action_error: str | None = None
    hints: list[str] = Field(default_factory=list)


class HelpfulAction(BaseModel):
    action: ActionType
    service: str | None = None


class RequiredAction(BaseModel):
    action: ActionType
    service: str | None = None


class ScenarioConfig(BaseModel):
    id: str
    name: str
    difficulty: str
    alert: str
    services: list[str]
    max_steps: int = Field(default=12, ge=1, le=20)

    root_cause: str
    root_cause_aliases: list[str]

    initial_visible_services: list[str] = Field(default_factory=list)
    initial_visible_logs: list[str] = Field(default_factory=list)
    hidden_logs: dict[str, list[str]] = Field(default_factory=dict)
    metrics: dict[str, ServiceMetrics] = Field(default_factory=dict)

    required_actions: list[RequiredAction] = Field(default_factory=list)
    helpful_actions: list[HelpfulAction] = Field(default_factory=list)

    wrong_diagnosis_penalty: float = Field(default=4.0, ge=0.0)
    resolution_bonus: float = Field(default=12.0, ge=0.0)


GpuModeAction.model_rebuild()
ScenarioConfig.model_rebuild()
