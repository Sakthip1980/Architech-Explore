"""Memory Controller model with scheduling policies"""
from typing import Dict, Any, Optional, List
from ..base import Module
import random


class MemoryController(Module):
    """
    Memory Controller model with scheduling policies.
    
    Features:
    - Request scheduling (FCFS, FR-FCFS, etc.)
    - Bank-level parallelism
    - Row buffer management
    - QoS support
    """
    
    def __init__(
        self,
        name: str = "MemCtrl",
        scheduling_policy: str = "FR-FCFS",  # FCFS, FR-FCFS, BLISS, ATLAS
        channels: int = 2,
        banks_per_channel: int = 16,
        queue_depth: int = 32,
        row_buffer_size_bytes: int = 8192,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.scheduling_policy = scheduling_policy
        self.channels = channels
        self.banks_per_channel = banks_per_channel
        self.queue_depth = queue_depth
        self.row_buffer_size_bytes = row_buffer_size_bytes
        
        # Per-bank row buffer state (simulated)
        self._open_rows = {}
        
        # Statistics
        self._row_buffer_hits = 0
        self._row_buffer_misses = 0
        self._row_buffer_conflicts = 0
        self._reordered_requests = 0
        
    def _schedule_request(self, bank_id: int, row_id: int) -> str:
        """Determine request outcome based on row buffer state"""
        current_row = self._open_rows.get(bank_id)
        
        if current_row is None:
            # Empty row buffer - just activate
            self._open_rows[bank_id] = row_id
            self._row_buffer_misses += 1
            return 'miss'
        elif current_row == row_id:
            # Row buffer hit!
            self._row_buffer_hits += 1
            return 'hit'
        else:
            # Row buffer conflict - need to precharge and activate new row
            self._open_rows[bank_id] = row_id
            self._row_buffer_conflicts += 1
            return 'conflict'
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate memory controller request handling"""
        self.metrics.total_requests += 1
        
        # Simulate bank and row selection (randomized for demo)
        bank_id = random.randint(0, self.channels * self.banks_per_channel - 1)
        row_id = random.randint(0, 1023)
        
        # Schedule request
        outcome = self._schedule_request(bank_id, row_id)
        
        # Latency based on outcome (in ns, assuming 2400MHz DDR4)
        if outcome == 'hit':
            base_latency = 15  # Just CAS latency
        elif outcome == 'miss':
            base_latency = 35  # tRCD + CAS
        else:  # conflict
            base_latency = 55  # tRP + tRCD + CAS
        
        # FR-FCFS can reorder to prioritize hits
        if self.scheduling_policy == 'FR-FCFS' and outcome == 'hit':
            self._reordered_requests += 1
            base_latency *= 0.9  # Slight improvement from reordering
        
        # Transfer time
        transfer_ns = size_bytes / 25.6  # ~25.6 GB/s per channel
        
        total_latency = base_latency + transfer_ns
        self.metrics.total_latency_ns += total_latency
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return controller bandwidth"""
        return 25.6 * self.channels  # GB/s
    
    def get_power(self) -> float:
        """Return controller power"""
        return 3.0 + (self.channels * 1.5)
    
    def get_row_buffer_hit_rate(self) -> float:
        """Calculate row buffer hit rate"""
        total = self._row_buffer_hits + self._row_buffer_misses + self._row_buffer_conflicts
        if total == 0:
            return 0.0
        return self._row_buffer_hits / total
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed memory controller status"""
        base_status = super().get_status()
        base_status.update({
            'policy': self.scheduling_policy,
            'channels': self.channels,
            'banks': self.banks_per_channel * self.channels,
            'row_buffer_hit_rate': self.get_row_buffer_hit_rate(),
            'hits': self._row_buffer_hits,
            'misses': self._row_buffer_misses,
            'conflicts': self._row_buffer_conflicts,
            'reordered': self._reordered_requests
        })
        return base_status
