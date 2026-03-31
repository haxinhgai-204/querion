# Observability (mini)

## Why
For thesis/demo: show how workflow executed, latency, retrieved chunks, model config.

## What to log (minimum)
- run: start/end timestamps, app_id, workflow_id, conversation_id, latency_ms, status
- steps: node_started/node_finished per node_id + node_type
- optional: token usage + model name

## Where
- Postgres tables runs + run_steps

## UI
- Simple list page or modal:
  - last 20 runs
  - click run -> show step timing table
