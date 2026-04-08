from __future__ import annotations

from typing import Any

from openenv.core import EnvClient
from openenv.core.client_types import StepResult as OpenEnvStepResult
from openenv.core.env_server.types import State

from incident_types import AgentAction, IncidentState


class ProdGuardEnvClient(EnvClient[AgentAction, IncidentState, State]):
    """HTTP client wrapper for the ProdGuard-RL OpenEnv environment."""

    def _step_payload(self, action: AgentAction) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": action.action.value}
        if action.service is not None:
            payload["service"] = action.service
        if action.cause is not None:
            payload["cause"] = action.cause
        if action.confidence is not None:
            payload["confidence"] = action.confidence
        return payload

    def _parse_result(self, payload: dict[str, Any]) -> OpenEnvStepResult[IncidentState]:
        state_payload = payload.get("state", payload.get("observation", {}))
        observation = IncidentState.model_validate(state_payload)
        return OpenEnvStepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict[str, Any]) -> State:
        # OpenEnv base State only requires step_count/episode_id tracking metadata.
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
