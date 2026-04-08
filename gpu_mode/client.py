# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Gpu Mode RL environment client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

from .models import GpuModeAction, GpuModeObservation


class GpuModeEnv(
    EnvClient[GpuModeAction, GpuModeObservation, State]
):
    """WebSocket/HTTP client for multi-step incident response episodes."""

    def _step_payload(self, action: GpuModeAction) -> Dict:
        """
        Convert GpuModeAction to JSON payload for step message.

        Args:
            action: GpuModeAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        payload = {"action": action.action.value}
        if action.service is not None:
            payload["service"] = action.service
        if action.cause is not None:
            payload["cause"] = action.cause
        if action.confidence is not None:
            payload["confidence"] = action.confidence
        if action.task is not None:
            payload["task"] = action.task
        return payload

    def _parse_result(self, payload: Dict) -> StepResult[GpuModeObservation]:
        """
        Parse server response into StepResult[GpuModeObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with GpuModeObservation
        """
        obs_data = payload.get("observation", {})
        observation = GpuModeObservation.model_validate({
            "alert": obs_data.get("alert", ""),
            "visible_logs": obs_data.get("visible_logs", []),
            "visible_metrics": obs_data.get("visible_metrics", {}),
            "services": obs_data.get("services", []),
            "step_count": obs_data.get("step_count", payload.get("step_count", 0)),
            "task": obs_data.get("task", "easy"),
            "resolved": obs_data.get("resolved", False),
            "score": obs_data.get("score"),
            "last_action_error": obs_data.get("last_action_error"),
            "hints": obs_data.get("hints", []),
            "done": payload.get("done", False),
            "reward": payload.get("reward"),
            "metadata": obs_data.get("metadata", {}),
        })

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )
