"""
simulator.engine — Simulation engines

Public API
----------
roofline(flops, read_bytes, write_bytes, hw_block) -> RooflineResult
RooflineResult   - cycles, bottleneck, arithmetic_intensity, …

AnalyticalEngine - fast roofline + DAG critical-path scheduler
AnalyticalResult - total_cycles, wall_time_s, energy, per_op list
OpResult         - per-op breakdown

EventDrivenEngine (Phase 5) - cycle-accurate jump-ahead scheduler
"""

from .roofline import roofline, RooflineResult
from .analytical import AnalyticalEngine, AnalyticalResult, OpResult
from .event_driven import EventDrivenEngine

__all__ = [
    'roofline', 'RooflineResult',
    'AnalyticalEngine', 'AnalyticalResult', 'OpResult',
    'EventDrivenEngine',
]
