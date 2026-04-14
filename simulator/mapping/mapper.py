"""
Mapper: assigns ops to hardware blocks and selects tile sizes.

Mapping dataclass: op_assignments, dataflow_specs, tile_sizes
Mapper.greedy()         — assign each op to default block; default tiles
Mapper.tile_sweep()     — power-of-2 tile sweep × dataflow modes; prune infeasible
Mapper.evaluate_mapping() — feeds tiled bytes into roofline + AnalyticalEngine
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math

from ..workload.ops import Op, GEMMOp, Conv2DOp
from ..workload.graph import OpGraph, OpNode
from ..engine.roofline import roofline, RooflineResult
from ..engine.analytical import AnalyticalEngine, AnalyticalResult
from .loop_nest import LoopNest
from .dataflow import DataflowMode, get_loop_nest
from .feasibility import check_feasibility


@dataclass
class Mapping:
    """
    A complete mapping specification.

    op_assignments : {op_name: block}   — which block runs each op
    dataflow_specs : {op_name: DataflowMode}
    tile_sizes     : {op_name: {dim: size}}
    """
    op_assignments: Dict[str, Any] = field(default_factory=dict)
    dataflow_specs: Dict[str, DataflowMode] = field(default_factory=dict)
    tile_sizes: Dict[str, Dict[str, int]] = field(default_factory=dict)


class Mapper:
    """
    Generates and evaluates hardware-to-workload mappings.

    Usage
    -----
    mapper = Mapper(graph, default_block)
    mapping = mapper.greedy()
    result  = mapper.evaluate_mapping(mapping)

    candidates = mapper.tile_sweep(tile_step=32, max_tiles=4,
                                    dataflow_modes=[DataflowMode.WEIGHT_STATIONARY,
                                                    DataflowMode.OUTPUT_STATIONARY])
    best = min(candidates, key=lambda r: r.total_cycles)
    """

    def __init__(
        self,
        graph: OpGraph,
        default_block,
        dtype_bytes: int = 2,
    ):
        self.graph = graph
        self.default_block = default_block
        self.dtype_bytes = dtype_bytes

    # ------------------------------------------------------------------
    # Greedy mapping
    # ------------------------------------------------------------------

    def greedy(self) -> Mapping:
        """
        Assign all ops to default_block with default tile sizes.
        Tile sizes come from the op's own loop_nest() suggestion.
        """
        mapping = Mapping()
        for node in self.graph._nodes:
            name = node.name
            blk_name = getattr(self.default_block, 'name', 'default')
            mapping.op_assignments[name] = self.default_block
            mapping.dataflow_specs[name] = DataflowMode.WEIGHT_STATIONARY
            # Default tile from op's own loop_nest
            tiles = {lv['name']: lv['tile_size']
                     for lv in node.op.loop_nest()}
            mapping.tile_sizes[name] = tiles
        return mapping

    # ------------------------------------------------------------------
    # Tile sweep
    # ------------------------------------------------------------------

    def tile_sweep(
        self,
        tile_step: int = 32,
        max_tiles: int = 4,
        dataflow_modes: Optional[List[DataflowMode]] = None,
    ) -> List[Tuple[Mapping, AnalyticalResult]]:
        """
        Generate candidate mappings by sweeping tile sizes and dataflow modes.

        Returns a list of (Mapping, AnalyticalResult) pairs for feasible candidates.
        Prunes infeasible mappings before running the engine.

        Parameters
        ----------
        tile_step   : base tile size; sweep powers-of-2 multiples
        max_tiles   : maximum multiplier (tile = tile_step * 2^i for i in range(max_tiles))
        dataflow_modes : list of DataflowMode values to try
        """
        if dataflow_modes is None:
            dataflow_modes = [DataflowMode.WEIGHT_STATIONARY,
                              DataflowMode.OUTPUT_STATIONARY]

        # Generate tile size candidates
        tile_sizes_to_try = [tile_step * (2 ** i) for i in range(max_tiles)]

        # Only sweep GEMM-like ops; passthrough others with default tiles
        results: List[Tuple[Mapping, AnalyticalResult]] = []
        base_mapping = self.greedy()

        for t in tile_sizes_to_try:
            for df_mode in dataflow_modes:
                mapping = Mapping(
                    op_assignments=dict(base_mapping.op_assignments),
                    dataflow_specs={},
                    tile_sizes={},
                )

                feasible = True
                for node in self.graph._nodes:
                    name = node.name
                    op = node.op
                    blk = base_mapping.op_assignments.get(name, self.default_block)

                    if isinstance(op, GEMMOp):
                        tile_m = min(t, op.M)
                        tile_k = min(t, op.K)
                        tile_n = min(t, op.N)
                        tiles = {'m': tile_m, 'k': tile_k, 'n': tile_n}
                        feas = check_feasibility(op, blk, tiles, self.dtype_bytes)
                        if not feas.feasible:
                            feasible = False
                            break
                    elif isinstance(op, Conv2DOp):
                        tiles = {
                            'n': 1,
                            'c': min(t, op.C),
                            'k': min(t, op.K),
                            'ho': min(t, op.Ho),
                            'wo': min(t, op.Wo),
                            'r': op.R,
                            's': op.S,
                        }
                        feas = check_feasibility(op, blk, tiles, self.dtype_bytes)
                        if not feas.feasible:
                            feasible = False
                            break
                    else:
                        tiles = {lv['name']: lv['tile_size']
                                 for lv in op.loop_nest()}

                    mapping.dataflow_specs[name] = df_mode
                    mapping.tile_sizes[name] = tiles

                if feasible:
                    result = self.evaluate_mapping(mapping)
                    results.append((mapping, result))

        return results

    # ------------------------------------------------------------------
    # Evaluate a mapping
    # ------------------------------------------------------------------

    def evaluate_mapping(
        self,
        mapping: Mapping,
        use_tiled_bytes: bool = True,
    ) -> AnalyticalResult:
        """
        Run the analytical engine with tiled memory traffic from the mapping.

        If use_tiled_bytes=True, bytes fed to roofline come from the
        LoopNest tiling analysis. Otherwise, untiled op bytes are used.
        """
        from ..engine.analytical import OpResult, AnalyticalResult
        from ..engine.roofline import roofline

        order = self.graph.topological_order()
        finish_cycle: Dict[OpNode, float] = {}
        op_results = []

        for node in order:
            name = node.name
            op = node.op
            blk = mapping.op_assignments.get(name, self.default_block)
            df_mode = mapping.dataflow_specs.get(name, DataflowMode.WEIGHT_STATIONARY)
            tiles = mapping.tile_sizes.get(name, {})
            blk_name = getattr(blk, 'name', str(blk))

            if use_tiled_bytes and isinstance(op, GEMMOp) and tiles:
                loop = get_loop_nest(
                    df_mode, op.M, op.K, op.N,
                    tile_m=tiles.get('m', 32),
                    tile_k=tiles.get('k', 32),
                    tile_n=tiles.get('n', 32),
                    dtype_bytes=self.dtype_bytes,
                )
                rb = loop.tiled_read_bytes()
                wb = loop.tiled_write_bytes()
            else:
                rb = op.read_bytes(self.dtype_bytes)
                wb = op.write_bytes(self.dtype_bytes)

            f  = op.flops()
            rf = roofline(f, rb, wb, blk, self.dtype_bytes)

            start = max((finish_cycle[dep] for dep in node.inputs), default=0.0)
            end   = start + rf.cycles
            finish_cycle[node] = end

            op_results.append(OpResult(
                name=name, flops=f, read_bytes=rb, write_bytes=wb,
                roofline=rf, start_cycle=start, end_cycle=end, block_name=blk_name,
            ))

        total_cycles = max(finish_cycle.values(), default=0.0)

        from ..engine.analytical import _get_frequency, _get_power
        freq = _get_frequency(self.default_block)
        wall_time = total_cycles / freq if freq > 0 else 0.0
        power = _get_power(self.default_block)
        energy = power * wall_time

        compute_c = sum(r.roofline.compute_cycles for r in op_results)
        memory_c  = sum(r.roofline.memory_cycles  for r in op_results)
        if compute_c > memory_c * 1.05:
            bottleneck = 'compute'
        elif memory_c > compute_c * 1.05:
            bottleneck = 'memory'
        else:
            bottleneck = 'balanced'

        return AnalyticalResult(
            total_cycles=total_cycles,
            wall_time_s=wall_time,
            total_energy_joules=energy,
            average_power_watts=power,
            total_flops=sum(r.flops for r in op_results),
            total_bytes=sum(r.read_bytes + r.write_bytes for r in op_results),
            system_bottleneck=bottleneck,
            per_op=op_results,
        )
