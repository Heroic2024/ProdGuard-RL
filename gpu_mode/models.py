# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the Gpu Mode Environment.

The gpu_mode environment is a simple test environment that echoes back messages.
"""

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class GpuModeAction(Action):
    """Action for the Gpu Mode environment - just a message to echo."""

    message: str = Field(..., description="Message to echo back")


class GpuModeObservation(Observation):
    """Observation from the Gpu Mode environment - the echoed message."""

    echoed_message: str = Field(default="", description="The echoed message")
    message_length: int = Field(default=0, description="Length of the echoed message")
