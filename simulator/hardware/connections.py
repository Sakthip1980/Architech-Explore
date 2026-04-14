"""
Transaction lifecycle model for inter-block communication.

TransactionState: CREATED → QUEUED → GRANTED → IN_FLIGHT → RECEIVED → COMPLETED

Connection: owns a queue of in-flight transactions; advances state on .tick().
Backpressure and contention emerge naturally from the queue capacity limit.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Deque
from collections import deque
import itertools

from .blocks import Block


class TransactionState(Enum):
    """Lifecycle states of a single transfer transaction."""
    CREATED    = auto()   # just constructed
    QUEUED     = auto()   # waiting in source buffer
    GRANTED    = auto()   # link arbitrated; transfer starting
    IN_FLIGHT  = auto()   # bytes travelling across the link
    RECEIVED   = auto()   # bytes arrived at destination buffer
    COMPLETED  = auto()   # consumer acknowledged delivery


@dataclass
class Transaction:
    """
    One data transfer request between two blocks.

    All cycle timestamps are filled in as the transaction moves through
    its lifecycle. None means the event has not happened yet.
    """
    id: int
    src: str                      # source block name
    dst: str                      # destination block name
    size_bytes: int
    state: TransactionState = TransactionState.CREATED

    # cycle timestamps (filled in by Connection.tick)
    cycle_created:   Optional[int] = None
    cycle_queued:    Optional[int] = None
    cycle_granted:   Optional[int] = None
    cycle_inflight:  Optional[int] = None
    cycle_received:  Optional[int] = None
    cycle_completed: Optional[int] = None

    # derived convenience
    @property
    def latency_cycles(self) -> Optional[int]:
        """End-to-end latency in cycles, or None if not yet completed."""
        if self.cycle_completed is not None and self.cycle_created is not None:
            return self.cycle_completed - self.cycle_created
        return None


# Global transaction ID counter
_tx_counter = itertools.count(1)


def make_transaction(src: str, dst: str, size_bytes: int,
                     current_cycle: int = 0) -> Transaction:
    """Convenience constructor that stamps the creation cycle."""
    tx = Transaction(
        id=next(_tx_counter),
        src=src,
        dst=dst,
        size_bytes=size_bytes,
        cycle_created=current_cycle,
    )
    return tx


class Connection:
    """
    A unidirectional link between two Block instances.

    Parameters
    ----------
    src_block          : source Block
    dst_block          : destination Block
    bandwidth_bytes_per_cycle : peak transfer rate (bytes/cycle)
    latency_cycles     : fixed pipeline latency before first byte arrives
    energy_per_bit     : energy cost in Joules per bit transferred
    shared             : True if this link is shared (contention possible)
    protocol           : label string (e.g. "AXI4", "PCIe5", "CXL2")
    queue_depth        : max in-flight transactions before backpressure
    """

    def __init__(
        self,
        src_block: Block,
        dst_block: Block,
        bandwidth_bytes_per_cycle: float = 64.0,
        latency_cycles: int = 10,
        energy_per_bit: float = 1e-12,
        shared: bool = False,
        protocol: str = 'generic',
        queue_depth: int = 32,
    ):
        self.src_block = src_block
        self.dst_block = dst_block
        self.bandwidth_bytes_per_cycle = bandwidth_bytes_per_cycle
        self.latency_cycles = latency_cycles
        self.energy_per_bit = energy_per_bit
        self.shared = shared
        self.protocol = protocol
        self.queue_depth = queue_depth

        self._queue: Deque[Transaction] = deque()
        self._in_flight: List[Transaction] = []   # sorted by cycle_granted
        self._completed: List[Transaction] = []

        # Statistics
        self.total_bytes_transferred: int = 0
        self.total_energy_joules: float = 0.0
        self.stall_cycles: int = 0       # cycles where queue was full

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_accept(self) -> bool:
        """True if the link's queue is not full."""
        return len(self._queue) < self.queue_depth

    def enqueue(self, tx: Transaction, current_cycle: int) -> bool:
        """
        Add a transaction to the input queue.
        Returns False (backpressure) if queue is full.
        """
        if not self.can_accept():
            self.stall_cycles += 1
            return False
        tx.state = TransactionState.QUEUED
        tx.cycle_queued = current_cycle
        self._queue.append(tx)
        return True

    def tick(self, current_cycle: int) -> List[Transaction]:
        """
        Advance the connection by one cycle.

        Grant model:
          - A transaction is granted when the link becomes free (non-shared)
            or when bandwidth is available this cycle (shared).
          - Completion cycle = grant_cycle + latency_cycles
                               + ceil(size_bytes / bandwidth_bytes_per_cycle)
          - This naturally models the transfer time of large payloads.

        Returns list of newly completed Transactions this cycle.
        """
        import math
        newly_completed: List[Transaction] = []

        # --- 1. Grant: start transfers from queue
        # For non-shared links: only one transfer at a time.
        # For shared links: grant as many as bandwidth allows.
        if self.shared:
            bytes_available = self.bandwidth_bytes_per_cycle
            while self._queue and bytes_available > 0:
                tx = self._queue.popleft()
                tx.state = TransactionState.GRANTED
                tx.cycle_granted = current_cycle
                transfer_cycles = math.ceil(tx.size_bytes / self.bandwidth_bytes_per_cycle)
                tx._completion_cycle = current_cycle + self.latency_cycles + transfer_cycles
                self._in_flight.append(tx)
                bytes_available -= tx.size_bytes
        else:
            # Non-shared: grant one transaction at a time (serialised)
            if self._queue and not self._in_flight:
                tx = self._queue.popleft()
                tx.state = TransactionState.GRANTED
                tx.cycle_granted = current_cycle
                transfer_cycles = math.ceil(tx.size_bytes / self.bandwidth_bytes_per_cycle)
                tx._completion_cycle = current_cycle + self.latency_cycles + transfer_cycles
                self._in_flight.append(tx)

        # --- 2. Complete in-flight transactions whose time has arrived
        still_flying: List[Transaction] = []
        for tx in self._in_flight:
            if current_cycle >= tx._completion_cycle:
                tx.state = TransactionState.RECEIVED
                tx.cycle_received = current_cycle
                tx.state = TransactionState.COMPLETED
                tx.cycle_completed = current_cycle
                self._completed.append(tx)
                self.total_bytes_transferred += tx.size_bytes
                self.total_energy_joules += tx.size_bytes * 8 * self.energy_per_bit
                newly_completed.append(tx)
            else:
                still_flying.append(tx)
        self._in_flight = still_flying

        return newly_completed

    # ------------------------------------------------------------------
    # Status and metrics
    # ------------------------------------------------------------------

    @property
    def utilization(self) -> float:
        """Fraction of bandwidth utilised (simple estimate)."""
        if not self._completed:
            return 0.0
        # bytes per cycle averaged over completed transactions
        if self._completed[-1].cycle_completed:
            span = max(self._completed[-1].cycle_completed, 1)
            return min(self.total_bytes_transferred /
                       (span * self.bandwidth_bytes_per_cycle), 1.0)
        return 0.0

    def get_status(self) -> dict:
        return {
            'src': self.src_block.name,
            'dst': self.dst_block.name,
            'protocol': self.protocol,
            'bandwidth_bytes_per_cycle': self.bandwidth_bytes_per_cycle,
            'latency_cycles': self.latency_cycles,
            'queue_depth': self.queue_depth,
            'queue_occupancy': len(self._queue),
            'in_flight': len(self._in_flight),
            'completed': len(self._completed),
            'total_bytes': self.total_bytes_transferred,
            'total_energy_j': self.total_energy_joules,
            'stall_cycles': self.stall_cycles,
        }

    def __repr__(self):
        return (f"Connection({self.src_block.name!r} -> {self.dst_block.name!r}, "
                f"protocol={self.protocol!r}, "
                f"bw={self.bandwidth_bytes_per_cycle}B/cycle, "
                f"lat={self.latency_cycles}cyc)")
