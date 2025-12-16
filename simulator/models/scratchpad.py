"""Scratchpad Memory model"""
from typing import Dict, Any, Optional
from ..base import Module


class Scratchpad(Module):
    """
    Scratchpad Memory (SPM) model.
    
    Characteristics:
    - Software-managed (no cache controller)
    - Deterministic access latency
    - Partitionable for different functions
    - Common in embedded systems and accelerators
    """
    
    def __init__(
        self,
        name: str = "Scratchpad",
        size_kb: int = 256,
        partitions: int = 4,
        access_latency_cycles: int = 1,
        frequency_ghz: float = 1.0,
        ports: int = 2,  # Read/write ports
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.size_kb = size_kb
        self.partitions = partitions
        self.access_latency_cycles = access_latency_cycles
        self.frequency_ghz = frequency_ghz
        self.ports = ports
        
        # Per-partition usage tracking
        self._partition_usage = [0] * partitions
        
    def get_partition_size(self) -> int:
        """Get size per partition in KB"""
        return self.size_kb // self.partitions
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Simulate scratchpad access.
        
        Scratchpad provides deterministic, low-latency access.
        """
        self.metrics.total_requests += 1
        
        # Deterministic latency - main advantage of scratchpad
        cycles = self.access_latency_cycles
        
        # Additional cycles for larger transfers
        bytes_per_cycle = 8 * self.ports  # 64-bit * ports
        transfer_cycles = max(1, size_bytes / bytes_per_cycle)
        
        total_cycles = cycles + transfer_cycles
        latency_ns = total_cycles / self.frequency_ghz
        
        # Track partition usage (simplified - round robin)
        partition = self.metrics.total_requests % self.partitions
        self._partition_usage[partition] += size_bytes
        
        self.metrics.total_latency_ns += latency_ns
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """Return scratchpad bandwidth in GB/s"""
        bytes_per_cycle = 8 * self.ports
        return bytes_per_cycle * self.frequency_ghz
    
    def get_power(self) -> float:
        """Return power in Watts"""
        # SRAM-based, scales with size
        return 0.1 * (self.size_kb / 64)  # ~0.1W per 64KB
    
    def get_utilization(self) -> Dict[str, Any]:
        """Get per-partition utilization"""
        partition_size = self.get_partition_size() * 1024
        utilization = {}
        for i, usage in enumerate(self._partition_usage):
            utilization[f'partition_{i}'] = {
                'bytes_accessed': usage,
                'utilization_pct': min(100, (usage / partition_size) * 100)
            }
        return utilization
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed scratchpad status"""
        base_status = super().get_status()
        base_status.update({
            'size_kb': self.size_kb,
            'partitions': self.partitions,
            'partition_size_kb': self.get_partition_size(),
            'access_latency_cycles': self.access_latency_cycles,
            'ports': self.ports,
            'deterministic_latency_ns': self.access_latency_cycles / self.frequency_ghz
        })
        return base_status
