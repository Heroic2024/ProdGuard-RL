from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_TYPES_PATH = Path(__file__).with_name("types.py")
_SPEC = spec_from_file_location("incident_gym_types", _TYPES_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load local types.py module")

_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

ActionType = _MODULE.ActionType
ServiceMetrics = _MODULE.ServiceMetrics
IncidentState = _MODULE.IncidentState
AgentAction = _MODULE.AgentAction
StepResult = _MODULE.StepResult
HelpfulAction = _MODULE.HelpfulAction
RequiredAction = _MODULE.RequiredAction
ScenarioConfig = _MODULE.ScenarioConfig

__all__ = [
    "ActionType",
    "ServiceMetrics",
    "IncidentState",
    "AgentAction",
    "StepResult",
    "HelpfulAction",
    "RequiredAction",
    "ScenarioConfig",
]