# Harmony Job Scheduler API

Small FastAPI service for **Client A** scheduling input. It validates request JSON, maps it to a canonical internal model, runs a scheduler, and returns either:

- a feasible schedule with KPIs, or
- a structured infeasible response.

## Tech and requirements

- Python **3.11+** (Docker image uses 3.12)
- Runtime dependencies in `requirements.txt` (`fastapi`, `pydantic`, `uvicorn`)
- Tests use `pytest`

## How to run the service

### Local

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://127.0.0.1:8000/health
- OpenAPI: http://127.0.0.1:8000/docs

### Docker

```bash
docker build -f dockerfile -t harmony-scheduler .
docker run --rm -p 8000:8000 harmony-scheduler
```

## How to run tests

From repository root:

```bash
python -m pytest tests/ -v
```

Via Docker:

```bash
docker build -f dockerfile -t harmony-scheduler .
docker run --rm harmony-scheduler python -m pytest tests/ -v
```

Note: API tests use `fastapi.testclient` and require `httpx` in the image.

Current tests cover:

- scheduler invariants (`tests/support.py` + `tests/test_scheduler.py`)
- KPI recomputation check
- infeasible scheduler behavior
- determinism (same input -> same output ordering)

## Approach (solver or heuristic)

I used a **greedy heuristic** (`scheduler/heuristic.py`) instead of CP-SAT/OR-Tools for this take-home.

This is similar to an event-driven approach. Instead of tracking one global clock, we pick the next available machine, assign the best compatible job for that machine, and then advance that machine's time.
This ensures only one job is executed in a machine time block, so there is no overlap.
We also track each job's elapsed time and current step, which helps enforce route precedence and choose an appropriate start time on a machine.
High-level idea:
Pick a resource -> assign the best compatible job -> block that resource from job start to end.

- Implemented objective: `min_tardiness`
- `settings.objective_mode` is still accepted and validated so adding another objective is localized

The scheduler enforces:

- capability eligibility
- no overlap per resource
- precedence inside each product route
- operation fully inside one working window
- horizon bounds
- family changeover gap before later operation
- non-preemptive operation execution

How hard constraints are enforced in the algorithm:

- Capability eligibility: a job step is only considered for resources whose capability set includes that step capability.
- No overlap per resource: each resource has a `next_available` time; once a step is assigned, the resource is blocked until the step end.
- Precedence inside each product route: each job tracks `current_step_index` and `next_available`; step `k+1` is never eligible before step `k` completes.
- Operation fully inside one working window: candidate starts are searched only where `start >= window_start` and `end <= window_end` for a single window.
- Horizon bounds: if a computed operation end exceeds the planning horizon, the schedule is rejected as infeasible.
- Family changeover gap: before starting a step, required setup time from previous family to current family is added and enforced in start-time feasibility.
- Non-preemptive execution: each step is scheduled as one contiguous block from `start` to `end` with no splitting across gaps/windows.

## Assumptions / tradeoffs

### Assumptions

- All timestamps are local site times (no timezone conversion)
- Initial setup cost is zero (`None -> family` changeover is treated as 0)
- Changeover is not modeled as its own assignment row; required setup time is enforced before the later operation
- Setup can happen during idle time before a job becomes ready
  - Example: task A ends at 10, task B ready at 20, changeover 15, earliest B start is 25 (not 35)

### Tradeoffs

- Greedy heuristic does **not** backtrack, so some feasible cases may still be returned as infeasible
- Job scoring uses estimated completion from current step onward with worst-case future changeover padding
- Deterministic and simple implementation, but no global optimality guarantee like a solver

## Short design note

### Request flow through the system

```text
HTTP JSON
  -> api/schemas.py (Pydantic validation)
  -> adapter/client_a.py (Client A -> canonical Model)
  -> scheduler/heuristic.py (build assignments)
  -> kpi/calculate.py (compute KPIResult)
  -> api/main.py (map to response schemas + datetime serialization)
```

### Canonical internal model

`core/models.py` defines:

- `Step`, `Job`, `Resource`, `Settings`, `Model`, `Assignment`, `KPIResult`

Core time representation is integer minutes from horizon start; API transport converts to/from datetimes.

### Where to add a second client input format

- Add a new adapter module (for example, `adapter/client_b.py`)
- Add route/factory selection in `api/main.py` to choose the right adapter

### Where to add a new objective

- Add enum/schema option in `api/schemas.py` and canonical settings if needed
- Add objective branch/strategy in `scheduler/heuristic.py`

### Where to add a new constraint

- Enforce the rule in `scheduler/heuristic.py`
- Optionally add schema validation in `api/schemas.py` if the constraint needs input-shape/value validation

## API surface

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/schedule` | Build schedule for Client A request |

### Success response (200)

`assignments` + `kpis`, where assignment times are ISO datetimes.

### Validation error (422)

Returned when request shape/values fail schema validation.

```json
{
  "error": "validation_error",
  "issues": [{ "path": "...", "code": "...", "message": "...", "input": null }]
}
```

### Infeasible response (422)

Returned when request is valid but no schedule is feasible.

```json
{
  "error": "infeasible",
  "why": ["Concrete reason", "..."]
}
```

## KPI definitions implemented

From `kpi/calculate.py`:

- `tardiness_minutes`: sum of `max(0, completion - due)` across products
- `changeover_count`: number of family transitions on each resource sequence
- `changeover_minutes`: summed matrix setup minutes for those transitions
- `makespan_minutes`: `max(end) - min(start)` across assignments
- `utilization_pct`: per resource, processing minutes / total calendar minutes * 100, rounded

## Simple visualization

Tiny text visualization prints a per-resource timeline and KPI snapshot.

Reference outputs:

- `outputs/sample_1.txt`
- `outputs/sample_2.txt`
- `outputs/sample_3.txt`
- `outputs/sample_error.txt`

These files are sample artifacts for demonstration (not auto-generated on every request).

## Project layout

```text
api/         # FastAPI transport layer
adapter/     # Client-specific request -> canonical model mapping
core/        # Canonical models + domain errors
scheduler/   # Heuristic scheduling logic
kpi/         # KPI computations from assignments
tests/       # pytest tests and schedule verification helpers
dockerfile
requirements.txt
pytest.ini
```