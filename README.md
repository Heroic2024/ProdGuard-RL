# ProdGuard-RL

Reinforcement learning environment where an AI agent performs DevOps incident response with partial observability.

## What is included

- FastAPI backend with environment endpoints:
  - GET /health
  - GET /tasks
  - POST /reset
  - POST /step
  - GET /state
- Browser frontend at GET /
- Deterministic scenarios: easy, medium, hard

## Run the app

1. Activate venv
	- PowerShell:
	  - .\.venv\Scripts\Activate.ps1
2. Install dependencies
	- pip install -r requirements.txt
3. Start server
	- python server.py
4. Open frontend
	- http://127.0.0.1:8000

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
