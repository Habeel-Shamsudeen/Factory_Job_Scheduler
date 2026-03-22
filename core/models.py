from dataclasses import dataclass
from typing import Dict, List, Tuple, Literal

@dataclass
class Step:
    capability: str
    duration: int


@dataclass
class Job:
    id: str
    family: str
    due: int
    steps: List[Step]


@dataclass
class Resource:
    id: str
    capabilities: List[str]
    windows: List[Tuple[int, int]]

@dataclass
class Assignment:
    product: str
    step_index: int
    capability: str
    resource: str
    start: int
    end: int

@dataclass
class Settings:
    time_limit_seconds: int
    objective_mode: Literal['min_tardiness']


@dataclass
class KPIResult:
    tardiness_minutes: int
    changeover_count: int
    changeover_minutes: int
    makespan_minutes: int
    utilization_pct: Dict[str, int]


@dataclass
class Model:
    jobs: List[Job]
    resources: List[Resource]
    changeover: Dict[str, Dict[str, int]]  # e.g. "standard->premium": {"standard": 20, "premium": 10} becomes {"standard": {"premium": 20, "standard": 0}, "premium": {"standard": 10, "premium": 0}}
    horizon_start: int
    horizon_end: int
    settings: Settings