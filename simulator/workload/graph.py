"""
OpGraph: a directed-acyclic graph of Op nodes.

Topology helpers:
  - topological_order()   Kahn's algorithm; raises CycleError if graph has cycles
  - critical_path_length() DAG longest-path DP (in op count units)
  - from_workload()        linear chain from existing Workload object

The analytical engine in simulator/engine/analytical.py consumes OpGraph.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from collections import deque

from .ops import Op, workload_to_ops


class CycleError(Exception):
    """Raised when the graph contains a dependency cycle."""


@dataclass(eq=False)   # use object identity for hash/eq; each node is unique
class OpNode:
    """One node in the computation graph."""
    op: Op
    inputs: List['OpNode'] = field(default_factory=list)   # predecessor nodes
    outputs: List['OpNode'] = field(default_factory=list)  # successor nodes
    assigned_block: Optional[str] = None  # block name chosen by mapper

    @property
    def name(self) -> str:
        return self.op.name

    def __repr__(self):
        return (f"OpNode('{self.op.name}', "
                f"in={[n.name for n in self.inputs]}, "
                f"out={[n.name for n in self.outputs]})")


class OpGraph:
    """
    Directed acyclic graph of OpNode objects.

    Example
    -------
    g = OpGraph()
    a = g.add_op(GEMMOp(512, 512, 512, name='GEMM_A'))
    b = g.add_op(AddOp(512*512, name='residual'), inputs=[a])
    order = g.topological_order()
    """

    def __init__(self, name: str = 'graph'):
        self.name = name
        self._nodes: List[OpNode] = []
        self._node_map: Dict[str, OpNode] = {}  # name → node (first match)

    # ------------------------------------------------------------------
    # Building the graph
    # ------------------------------------------------------------------

    def add_op(self, op: Op,
               inputs: Optional[List[OpNode]] = None) -> OpNode:
        """
        Add an Op to the graph and return its OpNode.

        Parameters
        ----------
        op     : the Op instance
        inputs : list of OpNode objects that must complete before this op
        """
        node = OpNode(op=op, inputs=list(inputs or []))
        for inp in node.inputs:
            inp.outputs.append(node)
        self._nodes.append(node)
        # Register in map (use op.name; keep first if duplicate names)
        if op.name not in self._node_map:
            self._node_map[op.name] = node
        return node

    def get_node(self, name: str) -> Optional[OpNode]:
        """Return node by op name, or None."""
        return self._node_map.get(name)

    # ------------------------------------------------------------------
    # Topology queries
    # ------------------------------------------------------------------

    def topological_order(self) -> List[OpNode]:
        """
        Return nodes in topological order using Kahn's algorithm.
        Raises CycleError if a cycle is detected.
        """
        in_degree: Dict[OpNode, int] = {n: len(n.inputs) for n in self._nodes}
        queue: deque = deque(n for n in self._nodes if in_degree[n] == 0)
        order: List[OpNode] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for succ in node.outputs:
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        if len(order) != len(self._nodes):
            raise CycleError(
                f"Graph '{self.name}' contains a cycle — "
                f"processed {len(order)}/{len(self._nodes)} nodes."
            )
        return order

    def critical_path_length(self) -> int:
        """
        Return the longest path through the graph (in number of ops).
        Uses DAG dynamic programming on topological order.
        """
        order = self.topological_order()
        dist: Dict[OpNode, int] = {n: 1 for n in self._nodes}
        for node in order:
            for succ in node.outputs:
                if dist[node] + 1 > dist[succ]:
                    dist[succ] = dist[node] + 1
        return max(dist.values()) if dist else 0

    def total_flops(self) -> float:
        """Sum of all op FLOPs in the graph."""
        return sum(n.op.flops() for n in self._nodes)

    def total_read_bytes(self, dtype_bytes: int = 2) -> float:
        """Sum of all op read bytes."""
        return sum(n.op.read_bytes(dtype_bytes) for n in self._nodes)

    def total_write_bytes(self, dtype_bytes: int = 2) -> float:
        """Sum of all op write bytes."""
        return sum(n.op.write_bytes(dtype_bytes) for n in self._nodes)

    # ------------------------------------------------------------------
    # Factory from existing Workload
    # ------------------------------------------------------------------

    @classmethod
    def from_workload(cls, workload, name: str = '') -> 'OpGraph':
        """
        Build a linear-chain OpGraph from an existing Workload object.

        Workload.layers → Op list → sequential dependency chain.
        """
        graph_name = name or getattr(workload, 'name', 'workload')
        g = cls(name=graph_name)
        ops = workload_to_ops(workload)
        prev: Optional[OpNode] = None
        for op in ops:
            node = g.add_op(op, inputs=[prev] if prev else None)
            prev = node
        return g

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self, dtype_bytes: int = 2) -> Dict[str, Any]:
        """Return a summary dict of graph statistics."""
        return {
            'name': self.name,
            'num_ops': len(self._nodes),
            'total_flops': self.total_flops(),
            'total_read_bytes': self.total_read_bytes(dtype_bytes),
            'total_write_bytes': self.total_write_bytes(dtype_bytes),
            'critical_path_ops': self.critical_path_length(),
        }

    def __len__(self) -> int:
        return len(self._nodes)

    def __repr__(self):
        return (f"OpGraph('{self.name}', {len(self._nodes)} ops, "
                f"{self.total_flops():.3g} FLOPs)")
