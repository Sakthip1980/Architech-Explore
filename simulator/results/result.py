"""
SimResult: unified simulation result wrapper.

Works for both AnalyticalEngine and EventDrivenEngine outputs.
Adds SensitivitySweep for varying one hardware property and
computing Pareto fronts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
import copy


@dataclass
class BlockStats:
    """Per-block activity statistics."""
    name: str
    active_cycles: float = 0.0
    stall_cycles: float = 0.0
    idle_cycles: float = 0.0
    bytes_transferred: float = 0.0

    @property
    def total_cycles(self) -> float:
        return self.active_cycles + self.stall_cycles + self.idle_cycles

    @property
    def utilization(self) -> float:
        t = self.total_cycles
        return self.active_cycles / t if t > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'active_cycles': self.active_cycles,
            'stall_cycles': self.stall_cycles,
            'idle_cycles': self.idle_cycles,
            'bytes_transferred': self.bytes_transferred,
            'utilization': self.utilization,
        }


@dataclass
class SimResult:
    """
    Unified simulation result, wrapping AnalyticalResult.

    Adds per-block stats and convenience accessors.
    """
    total_cycles: float
    wall_time_s: float
    total_energy_j: float
    avg_power_w: float
    total_flops: float
    total_bytes: float
    system_bottleneck: str
    block_stats: List[BlockStats] = field(default_factory=list)
    per_op: List[Any] = field(default_factory=list)   # OpResult list
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_analytical(cls, result, label: str = '') -> 'SimResult':
        """Convert AnalyticalResult to SimResult."""
        # Extract block stats from power_breakdown if available
        bstats = []
        if result.power_breakdown:
            for name, info in result.power_breakdown.items():
                bstats.append(BlockStats(
                    name=name,
                    active_cycles=info.get('active_cycles', 0),
                    idle_cycles=info.get('idle_cycles', 0),
                    bytes_transferred=sum(
                        r.read_bytes + r.write_bytes
                        for r in result.per_op
                        if r.block_name == name
                    ),
                ))
        return cls(
            total_cycles=result.total_cycles,
            wall_time_s=result.wall_time_s,
            total_energy_j=result.total_energy_joules,
            avg_power_w=result.average_power_watts,
            total_flops=result.total_flops,
            total_bytes=result.total_bytes,
            system_bottleneck=result.system_bottleneck,
            block_stats=bstats,
            per_op=result.per_op,
            metadata={'label': label},
        )

    def summary(self) -> Dict[str, Any]:
        return {
            'total_cycles': self.total_cycles,
            'wall_time_ms': self.wall_time_s * 1000,
            'total_energy_j': self.total_energy_j,
            'avg_power_w': self.avg_power_w,
            'total_flops': self.total_flops,
            'total_bytes': self.total_bytes,
            'system_bottleneck': self.system_bottleneck,
            'num_ops': len(self.per_op),
            'label': self.metadata.get('label', ''),
        }


# ---------------------------------------------------------------------------
# Sensitivity sweep
# ---------------------------------------------------------------------------

class SensitivitySweep:
    """
    Vary one hardware property over a range of values, run simulation,
    collect results.

    Usage
    -----
    from simulator.results import SensitivitySweep
    from simulator.engine import AnalyticalEngine

    sweep = SensitivitySweep(graph, default_block, AnalyticalEngine())
    results = sweep.vary('BW', [32e9, 64e9, 128e9, 256e9, 512e9])
    pareto = SensitivitySweep.pareto_front(results, 'total_cycles', 'total_energy_j')
    """

    def __init__(self, graph, base_block, engine=None):
        self.graph = graph
        self.base_block = base_block
        # Defer engine import to avoid circular imports
        if engine is None:
            from ..engine.analytical import AnalyticalEngine
            engine = AnalyticalEngine()
        self.engine = engine

    def vary(
        self,
        property_name: str,
        values: List[float],
        label_format: str = '{name}={value:.3g}',
    ) -> List[SimResult]:
        """
        Run simulation for each value of property_name.

        Returns list of SimResult (one per value).
        """
        from ..hardware.blocks import Block
        results = []
        for val in values:
            # Deep-copy the block so we don't mutate the original
            blk_copy = self._clone_block(self.base_block, property_name, val)
            label = label_format.format(name=property_name, value=val)
            try:
                raw = self.engine.run(self.graph, blk_copy)
                sr = SimResult.from_analytical(raw, label=label)
                sr.metadata[property_name] = val
                results.append(sr)
            except Exception as e:
                # Skip failed configs (e.g. solver conflict)
                pass
        return results

    def _clone_block(self, block, prop_name: str, prop_val: float):
        """Create a copy of block with one property overridden."""
        from ..hardware.blocks import Block, ComputeBlock, MemoryBlock, InterconnectBlock

        cls = block.__class__
        new_blk = cls(block.name + '_sweep')

        # Copy existing schema values
        for name, node in block._schema._nodes.items():
            if node.value is not None and node.source == 'user':
                new_blk._schema.set(name, node.value)

        # Apply override
        new_blk._schema.set(prop_name, prop_val)
        return new_blk

    @staticmethod
    def pareto_front(
        results: List[SimResult],
        x_metric: str,
        y_metric: str,
    ) -> List[SimResult]:
        """
        Dominance filter: return Pareto-optimal results.

        A result is dominated if another has both lower x_metric AND
        lower y_metric. Non-dominated results form the Pareto front.

        x_metric, y_metric: attribute names on SimResult
        """
        def get_val(r: SimResult, metric: str) -> float:
            if hasattr(r, metric):
                return getattr(r, metric)
            return r.metadata.get(metric, float('inf'))

        pareto = []
        for r in results:
            rx = get_val(r, x_metric)
            ry = get_val(r, y_metric)
            dominated = False
            for other in results:
                if other is r:
                    continue
                ox = get_val(other, x_metric)
                oy = get_val(other, y_metric)
                if ox <= rx and oy <= ry and (ox < rx or oy < ry):
                    dominated = True
                    break
            if not dominated:
                pareto.append(r)

        # Sort by x_metric
        pareto.sort(key=lambda r: get_val(r, x_metric))
        return pareto
