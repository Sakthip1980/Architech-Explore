"""
simulator.mapping — Mapping and dataflow layer

Public API
----------
LoopVar            - one loop dimension with tile size and memory level
LoopNest           - tiled loop nest; presets: weight_stationary, output_stationary, input_stationary
DataflowMode       - enum: WEIGHT_STATIONARY, OUTPUT_STATIONARY, INPUT_STATIONARY, BEST
get_loop_nest()    - factory for LoopNest given mode and GEMM dims
FeasibilityResult  - feasibility check result
check_feasibility()- check tile sizes against hw memory capacity
Mapping            - op_assignments + dataflow_specs + tile_sizes
Mapper             - greedy(), tile_sweep(), evaluate_mapping()
"""

from .loop_nest import LoopVar, LoopNest
from .dataflow import DataflowMode, get_loop_nest
from .feasibility import FeasibilityResult, check_feasibility
from .mapper import Mapping, Mapper

__all__ = [
    'LoopVar', 'LoopNest',
    'DataflowMode', 'get_loop_nest',
    'FeasibilityResult', 'check_feasibility',
    'Mapping', 'Mapper',
]
