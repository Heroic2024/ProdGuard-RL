---
title: ProdGuard-RL
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
app_file: app.py
pinned: false
---

# ProdGuard-RL

ProdGuard-RL is an interactive reinforcement learning environment for incident response in production systems.
It simulates real DevOps triage workflows where an agent must investigate noisy signals, take corrective actions,
and identify root cause under partial observability.

The project is designed for:
- Evaluating LLM-based and policy-based responders on realistic multi-step incidents.
- Benchmarking decision quality, efficiency, and diagnosis confidence.
- Deploying as a Hugging Face Docker Space with both API and web interface.

## Core Idea

Each episode presents an alert and limited telemetry. The agent can:
- Inspect logs and metrics for specific services.
- Apply remediation actions (restart, scale, rollback).
- Declare root cause with confidence.

Rewards encourage good operational behavior:
- Fast, relevant investigation.
- Correct remediation sequence.
- Accurate root-cause declaration.
- Minimal unnecessary actions.

## What is included

- FastAPI backend with environment endpoints:
  - GET /health
  - GET /tasks
  - POST /reset
  - POST /step
  - GET /state
- Browser frontend at GET /
- Deterministic scenarios: easy, medium, hard
- Typed action/state models for reproducible interaction contracts
- Inference runner for benchmark-style multi-task evaluation

## Project Structure

- app.py: Docker/Space entrypoint FastAPI app
- env.py: Environment engine and episode lifecycle
- scenarios/: Scenario definitions and task catalog
- inference.py: Baseline benchmark runner with structured logs
- grader.py: Deterministic scoring utilities
- frontend/: Browser UI for interactive control room
- server.py: Local development server module

## Environment API

- POST /reset
  - Input: task selector
  - Output: initial observation/state
- POST /step
  - Input: agent action payload
  - Output: next state, reward, done, and metadata
- GET /state
  - Output: current observation snapshot
- GET /tasks
  - Output: available tasks
- GET /health
  - Output: service liveness

## Run the app

1. Activate virtual environment
	- PowerShell: .\.venv\Scripts\Activate.ps1
2. Install dependencies
	- pip install -r requirements.txt
3. Start local API + UI server
	- python server.py
4. Open UI
	- http://127.0.0.1:8000

## Run benchmark inference

1. Start server (if not already running)
	- python server.py
2. Run inference benchmark
	- python inference.py

The runner emits structured logs per task:
- [START] task metadata
- [STEP] action, reward, done, error
- [END] success, steps, score, reward trace

## Hugging Face Space

This repository is configured for Docker-based Hugging Face Space deployment.

Primary deployment command:
- openenv push --repo-id HeroicCoder168/ProdGuardRL

After deploy:
- Runtime app URL: https://heroiccoder168-prodguardrl.hf.space
- Space page: https://huggingface.co/spaces/HeroicCoder168/ProdGuardRL

## Quick API sanity checks

Run these in another PowerShell terminal while the server is running.

1. Health
	- Invoke-RestMethod http://127.0.0.1:8000/health
2. Tasks
	- Invoke-RestMethod http://127.0.0.1:8000/tasks
3. Reset (easy)
	- Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/reset -ContentType application/json -Body '{"task":"easy"}'
4. Step
	- Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/step -ContentType application/json -Body '{"action":"check_logs","service":"db"}'
5. State
	- Invoke-RestMethod http://127.0.0.1:8000/state

## End-to-end episode check

This sequence should finish an easy episode and return done=True with a score.

PowerShell:

$base='http://127.0.0.1:8000'
Invoke-RestMethod -Method Post -Uri "$base/reset" -ContentType 'application/json' -Body '{"task":"easy"}' | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/step" -ContentType 'application/json' -Body '{"action":"check_metrics","service":"db"}' | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/step" -ContentType 'application/json' -Body '{"action":"check_logs","service":"db"}' | Out-Null
Invoke-RestMethod -Method Post -Uri "$base/step" -ContentType 'application/json' -Body '{"action":"restart_service","service":"db"}' | Out-Null
$final = Invoke-RestMethod -Method Post -Uri "$base/step" -ContentType 'application/json' -Body '{"action":"declare_root_cause","cause":"database outage","confidence":0.92}'
$final

Expected:
- $final.done is True
- $final.info.score is present


