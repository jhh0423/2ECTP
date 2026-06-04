from dataclasses import dataclass


@dataclass
class Demand:
    id: int
    x: float
    y: float
    demand: float = 0.0
    service_time: float = 0.0


@dataclass
class Cover:
    id: int
    x: float
    y: float
    service_time: float = 0.0


@dataclass
class Hub:
    id: int
    x: float
    y: float
    service_time: float = 0.0


@dataclass
class Instance:
    NAME: str
    CAPACITY1: float
    CAPACITY2: float
    COST1: float
    COST2: float
    TIME1: float
    TIME2: float
    TIME3: float
    DEPOT: tuple[float, float] | None

    demands: list[Demand]
    covers: list[Cover]
    hubs: list[Hub]
