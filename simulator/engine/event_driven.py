"""
Event-driven simulation engine with jump-ahead clock.

Unlike the analytical engine (which sums roofline cycles per op),
the event-driven engine simulates op execution cycle-by-cycle with
actual dependency tracking:

  1. Start with all ops whose inputs are satisfied (in-degree=0).
  2. Schedule each ready op on its assigned block (earliest-free slot).
  3. Jump the clock to the next event (op completion).
  4. Release dependent ops; repeat until done.

DMA/compute overlap emerges automatically: if two ops are on different
blocks and have no data dependency, they run concurrently.

Tracks per-block active_cycles, stall_cycles, idle_cycles.
"""

import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set, Tuple

from ..workload.graph import OpGraph, OpNode
from ..engine.roofline import roofline, RooflineResult
from ..engine.analytical import AnalyticalResult, OpResult


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass(order=True)
class Event:
    """A simulation event at a specific cycle."""
    cycle: float                         # when this event fires
    event_type: str = field(compare=False)  # 'op_complete'
    payload: Any    = field(compare=False)  # node, block, rf_result, ...


class EventQueue:
    """Min-heap priority queue on cycle."""

    def __init__(self):
        self._heap: List[Event] = []

    def push(self, event: Event):
        heapq.heappush(self._heap, event)

    def pop(self) -> Optional[Event]:
        if self._heap:
            return heapq.heappop(self._heap)
        return None

    def __len__(self) -> int:
        return len(self._heap)


# ---------------------------------------------------------------------------
# Block state tracker (for event-driven scheduling)
# ---------------------------------------------------------------------------

@dataclass
class BlockState:
    """Runtime state of a hardware block during event-driven simulation."""
    name: str
    free_at_cycle: float = 0.0    # earliest cycle block can start new op
    active_cycles: float = 0.0
    idle_cycles: float = 0.0
    ops_completed: int = 0


# ---------------------------------------------------------------------------
# EventDrivenEngine
# ---------------------------------------------------------------------------

class EventDrivenEngine:
    """
    Cycle-accurate event-driven simulation engine.

    Usage
    -----
    from simulator.engine.event_driven import EventDrivenEngine
    from simulator.mapping import Mapper, DataflowMode

    engine = EventDrivenEngine()
    result = engine.run(graph, default_block)
    print(result.total_cycles)
    """

    def __init__(self, dtype_bytes: int = 2):
        self.dtype_bytes = dtype_bytes

    def run(
        self,
        graph: OpGraph,
        default_block,
        block_map: Optional[Dict[str, Any]] = None,
        read_bytes_map: Optional[Dict[str, float]] = None,
        write_bytes_map: Optional[Dict[str, float]] = None,
    ) -> AnalyticalResult:
        """
        Simulate graph with event-driven scheduling.

        Parameters
        ----------
        graph           : OpGraph to simulate
        default_block   : default hardware block
        block_map       : {op_name: block} per-op override
        read_bytes_map  : {op_name: bytes} tiled read bytes (from mapper)
        write_bytes_map : {op_name: bytes} tiled write bytes

        Returns
        -------
        AnalyticalResult with per-block utilisation statistics.
        """
        block_map      = block_map      or {}
        read_bytes_map = read_bytes_map or {}
        write_bytes_map = write_bytes_map or {}

        # --- Setup
        in_degree: Dict[OpNode, int] = {}
        for node in graph._nodes:
            in_degree[node] = len(node.inputs)

        # Block state: one entry per unique block name
        block_states: Dict[str, BlockState] = {}

        def _get_block(node):
            return block_map.get(node.name, default_block)

        def _block_name(blk) -> str:
            return getattr(blk, 'name', str(blk))

        def _ensure_state(blk_name: str):
            if blk_name not in block_states:
                block_states[blk_name] = BlockState(name=blk_name)

        # Initialise states
        _ensure_state(_block_name(default_block))
        for blk in block_map.values():
            _ensure_state(_block_name(blk))

        # Ready queue: nodes with in_degree==0
        eq = EventQueue()
        finish_cycle: Dict[OpNode, float] = {}
        op_results: List[OpResult] = []
        current_clock = 0.0

        # Seed: all ops with no predecessors
        for node in graph._nodes:
            if in_degree[node] == 0:
                _schedule(node, 0.0, eq, default_block, block_map,
                          block_states, read_bytes_map, write_bytes_map,
                          self.dtype_bytes)

        # --- Main event loop
        while len(eq) > 0:
            evt = eq.pop()
            node, blk, rf = evt.payload
            blk_name = _block_name(blk)
            _ensure_state(blk_name)
            state = block_states[blk_name]

            # Record completion
            complete_cycle = evt.cycle
            finish_cycle[node] = complete_cycle
            state.ops_completed += 1

            op = node.op
            start_c = complete_cycle - rf.cycles
            state.active_cycles += rf.cycles

            rb = read_bytes_map.get(node.name, op.read_bytes(self.dtype_bytes))
            wb = write_bytes_map.get(node.name, op.write_bytes(self.dtype_bytes))

            op_results.append(OpResult(
                name=node.name,
                flops=op.flops(),
                read_bytes=rb,
                write_bytes=wb,
                roofline=rf,
                start_cycle=start_c,
                end_cycle=complete_cycle,
                block_name=blk_name,
            ))

            # Propagate to successors
            for succ in node.outputs:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    # All deps satisfied; earliest start = latest parent finish
                    earliest = max(finish_cycle[dep] for dep in succ.inputs)
                    _schedule(succ, earliest, eq, default_block, block_map,
                              block_states, read_bytes_map, write_bytes_map,
                              self.dtype_bytes)

        total_cycles = max(finish_cycle.values(), default=0.0)

        # --- Compute idle cycles per block
        for state in block_states.values():
            state.idle_cycles = max(0.0, total_cycles - state.active_cycles)

        # --- Aggregate result
        from ..engine.analytical import _get_frequency, _get_power
        freq = _get_frequency(default_block)
        wall_time = total_cycles / freq if freq > 0 else 0.0
        power = _get_power(default_block)
        energy = power * wall_time

        compute_c = sum(r.roofline.compute_cycles for r in op_results)
        memory_c  = sum(r.roofline.memory_cycles  for r in op_results)
        if compute_c > memory_c * 1.05:
            bottleneck = 'compute'
        elif memory_c > compute_c * 1.05:
            bottleneck = 'memory'
        else:
            bottleneck = 'balanced'

        # Embed block utilisation in power_breakdown field
        util_data = {
            name: {
                'active_cycles': s.active_cycles,
                'idle_cycles': s.idle_cycles,
                'ops_completed': s.ops_completed,
                'utilization': s.active_cycles / total_cycles if total_cycles > 0 else 0.0,
            }
            for name, s in block_states.items()
        }

        return AnalyticalResult(
            total_cycles=total_cycles,
            wall_time_s=wall_time,
            total_energy_joules=energy,
            average_power_watts=power,
            total_flops=sum(r.flops for r in op_results),
            total_bytes=sum(r.read_bytes + r.write_bytes for r in op_results),
            system_bottleneck=bottleneck,
            per_op=op_results,
            power_breakdown=util_data,
        )


def _schedule(
    node: OpNode,
    earliest_start: float,
    eq: EventQueue,
    default_block,
    block_map: Dict,
    block_states: Dict[str, BlockState],
    read_bytes_map: Dict,
    write_bytes_map: Dict,
    dtype_bytes: int,
):
    """Schedule one node onto its block, respecting block availability."""
    blk = block_map.get(node.name, default_block)
    blk_name = getattr(blk, 'name', str(blk))
    if blk_name not in block_states:
        block_states[blk_name] = BlockState(name=blk_name)
    state = block_states[blk_name]

    op = node.op
    rb = read_bytes_map.get(node.name, op.read_bytes(dtype_bytes))
    wb = write_bytes_map.get(node.name, op.write_bytes(dtype_bytes))
    rf = roofline(op.flops(), rb, wb, blk, dtype_bytes)

    # Start no earlier than: requested earliest OR block becomes free
    actual_start = max(earliest_start, state.free_at_cycle)
    complete_at  = actual_start + rf.cycles

    # Mark block busy until this op finishes
    state.free_at_cycle = complete_at

    eq.push(Event(
        cycle=complete_at,
        event_type='op_complete',
        payload=(node, blk, rf),
    ))
