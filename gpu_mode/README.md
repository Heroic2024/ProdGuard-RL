# GPU Mode Incident RL Environment

Gpu Mode is now a multi-task reinforcement learning environment for DevOps incident response.

## What It Provides

- OpenEnv-compatible server with reset/step/state endpoints
- Typed Pydantic action and observation models
- Three deterministic tasks:
  - easy: database down
  - medium: API memory leak with ambiguous signals
  - hard: cache -> db -> api cascade failure
- Partial observability (logs/metrics are revealed through actions)
- Deterministic grader in [0.0, 1.0] combining correctness, efficiency, and action quality

## Key Actions

- check_logs(service)
- check_metrics(service)
- restart_service(service)
- scale_service(service)
- rollback_deployment()
- declare_root_cause(cause, confidence)
- select_task(task) for selecting the next episode task

## Task Selection

The OpenEnv reset request supports seed and episode_id.
To choose a task at reset, pass:

- episode_id=task:easy
- episode_id=task:medium
- episode_id=task:hard

If not provided, tasks rotate deterministically across resets.

## Local Run

```bash
uvicorn server.app:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest -q
```

## Inference Script

`inference.py` uses OpenAI client with:

- API_BASE_URL
- MODEL_NAME
- HF_TOKEN
- optional: LOCAL_IMAGE_NAME, TASK, MAX_STEPS

It prints benchmark logs in the required format:

- [START] ...
- [STEP] ...
- [END] ...
