# Harmony Job Scheduler API

I built this as a small FastAPI service for **Client A** scheduling input.
It validates request JSON, maps it into a canonical internal model, runs a heuristic scheduler, and returns either:

- a feasible schedule with KPIs, or
- a structured infeasible response.

## Tech and requirements

- Python **3.11+** (Docker image uses 3.12)
- Runtime dependencies in `requirements.txt` (`fastapi`, `pydantic`, `uvicorn`)
- Tests use `pytest`

## Run locally

From repository root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: http://127.0.0.1:8000/health
- OpenAPI: http://127.0.0.1:8000/docs

## Run with Docker

```bash
docker build -f dockerfile -t harmony-scheduler .
docker run --rm -p 8000:8000 harmony-scheduler
```

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

## My approach

I used a **greedy heuristic** (`scheduler/heuristic.py`) instead of CP-SAT/OR-Tools for this take-home.

### Objective

- Implemented objective: `min_tardiness`
- `settings.objective_mode` is still accepted and validated so adding another objective is localized.

### Constraint handling

The scheduler enforces:

- capability eligibility
- no overlap per resource
- precedence inside each product route
- operation fully inside one working window
- horizon bounds
- family changeover gap before later operation
- non-preemptive operation execution

## Request flow and boundaries

```text
HTTP JSON
  -> api/schemas.py (Pydantic validation)
  -> adapter/client_a.py (Client A -> canonical Model)
  -> scheduler/heuristic.py (build assignments)
  -> kpi/calculate.py (compute KPIResult)
  -> api/main.py (map to response schemas + datetime serialization)
```

### Canonical internal model

`core/models.py` contains:

- `Step`, `Job`, `Resource`, `Settings`, `Model`, `Assignment`, `KPIResult`

Core time representation is integer minutes from horizon start.
The API layer handles datetime conversion for transport.

## Extension points

| Change needed later | Where I would add it |
|---------------------|----------------------|
| Second client format | Add new adapter module (ex: `adapter/client_b.py`) and route/factory selection in `api/main.py` |
| New objective mode | Add enum/schema option + objective branch/strategy in scheduler |
| New constraint | Enforce in scheduler; optional schema validation if it is input-shape related |
| KPI formula changes | `kpi/calculate.py` only |

## KPI definitions implemented

From `kpi/calculate.py`:

- `tardiness_minutes`: sum of `max(0, completion - due)` across products
- `changeover_count`: number of family transitions on each resource sequence
- `changeover_minutes`: summed matrix setup minutes for those transitions
- `makespan_minutes`: `max(end) - min(start)` across assignments
- `utilization_pct`: per resource, processing minutes / total calendar minutes * 100, rounded

## Tests

Run from repository root:

```bash
python -m pytest tests/ -v
```

Run tests via Docker:

```bash
docker build -f dockerfile -t harmony-scheduler .
docker run --rm harmony-scheduler python -m pytest tests/ -v
```

Note: API tests use `fastapi.testclient` and require `httpx` to be installed in the image.

Current tests cover:

- scheduler invariants (`tests/support.py` + `tests/test_scheduler.py`)
- KPI recomputation check
- infeasible scheduler behavior
- determinism (same input -> same output ordering)

## Simple visualization

Added a tiny text visualization that prints a per-resource timeline and KPI snapshot.

Reference visualization outputs are checked in here:

- `outputs/sample_1.txt`
- `outputs/sample_2.txt`
- `outputs/sample_3.txt`
- `outputs/sample_error.txt`

These files are sample artifacts for demonstration (not auto-generated on every request).


## Assumptions I made

- All timestamps are local site times (no timezone conversion).
- Initial setup cost is zero (`None -> family` changeover is treated as 0).
- I do not model changeover as its own assignment row.
  I enforce that required setup time exists before the later operation.
- Setup can happen during idle time before a job becomes ready.
  Example:
  - task A ends at 10
  - premium task B becomes ready at 20
  - changeover = 15
  - earliest start for B is 25 (not 35), because setup can begin at 10.

## Tradeoffs

- Because this is heuristic and greedy, it does **not** backtrack.
  So in some edge cases it can return infeasible even when another sequence might be feasible.
- Job scoring uses estimated completion from current step onward.
  I include worst-case future changeovers as padding, so estimate is intentionally approximate.
- This keeps the system deterministic and simple, but does not guarantee global optimality like a solver.

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