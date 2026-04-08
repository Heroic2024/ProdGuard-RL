from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ActionType(str, Enum):
    CHECK_LOGS = "check_logs"
    CHECK_METRICS = "check_metrics"
    RESTART_SERVICE = "restart_service"
    SCALE_SERVICE = "scale_service"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    DECLARE_ROOT_CAUSE = "declare_root_cause"


class ServiceMetrics(BaseModel):
    cpu_pct: float = Field(ge=0.0, le=100.0)
    memory_pct: float = Field(ge=0.0, le=100.0)
    error_rate: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    rps: float = Field(ge=0.0)


class IncidentState(BaseModel):
    alert: str
    visible_logs: list[str] = Field(default_factory=list)
    visible_metrics: dict[str, ServiceMetrics] = Field(default_factory=dict)
    services: list[str] = Field(default_factory=list)
    step_count: int = Field(default=0, ge=0)


class AgentAction(BaseModel):
    action: ActionType
    service: str | None = None
    cause: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_action_payload(self) -> "AgentAction":
        if self.action in {
            ActionType.CHECK_LOGS,
            ActionType.CHECK_METRICS,
            ActionType.RESTART_SERVICE,
            ActionType.SCALE_SERVICE,
        } and not self.service:
            raise ValueError("service is required for service-scoped actions")

        if self.action == ActionType.ROLLBACK_DEPLOYMENT:
            if self.service is not None or self.cause is not None:
                raise ValueError("rollback_deployment only accepts action")

        if self.action == ActionType.DECLARE_ROOT_CAUSE:
            if not self.cause:
                raise ValueError("cause is required for declare_root_cause")
            if self.confidence is None:
                raise ValueError("confidence is required for declare_root_cause")

        return self


class StepResult(BaseModel):
    state: IncidentState
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


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


AgentAction.model_rebuild()
HelpfulAction.model_rebuild()
RequiredAction.model_rebuild()
ScenarioConfig.model_rebuild()
