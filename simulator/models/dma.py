"""DMA Engine model"""
from typing import Dict, Any, Optional
from ..base import Module


class DMAEngine(Module):
    """
    DMA (Direct Memory Access) Engine model.
    
    Features:
    - CPU offload for memory transfers
    - Scatter-gather support
    - Multiple channels
    """
    
    def __init__(
        self,
        name: str = "DMA",
        channels: int = 8,
        max_burst_bytes: int = 4096,
        bandwidth_gbps: float = 25.6,
        scatter_gather: bool = True,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.channels = channels
        self.max_burst_bytes = max_burst_bytes
        self.bandwidth_gbps = bandwidth_gbps
        self.scatter_gather = scatter_gather
        
        # DMA setup latency (ns)
        self._setup_latency = 500
        
        # Bytes transferred
        self._total_bytes_transferred = 0
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate DMA transfer"""
        self.metrics.total_requests += 1
        
        # DMA setup overhead
        setup_latency = self._setup_latency
        
        # Calculate number of bursts needed
        num_bursts = max(1, (size_bytes + self.max_burst_bytes - 1) // self.max_burst_bytes)
        
        # Scatter-gather reduces overhead for multiple descriptors
        if self.scatter_gather and num_bursts > 1:
            descriptor_overhead = num_bursts * 10  # 10ns per descriptor
        else:
            descriptor_overhead = num_bursts * 50  # Non-SG: more overhead
        
        # Transfer time
        transfer_ns = (size_bytes / (self.bandwidth_gbps * 1e9)) * 1e9
        
        total_latency = setup_latency + descriptor_overhead + transfer_ns
        
        self._total_bytes_transferred += size_bytes
        self.metrics.total_latency_ns += total_latency
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return DMA bandwidth"""
        return self.bandwidth_gbps
    
    def get_power(self) -> float:
        """Return power in Watts"""
        # DMA engine is relatively low power
        return 2.0 + (self.channels * 0.2)
    
    def get_cpu_offload_benefit(self) -> Dict[str, float]:
        """Calculate CPU cycles saved by using DMA"""
        # Estimate CPU cycles that would be needed for memcpy
        bytes_per_cycle = 8  # Typical CPU memcpy throughput
        cpu_cycles_saved = self._total_bytes_transferred / bytes_per_cycle
        return {
            'bytes_transferred': self._total_bytes_transferred,
            'cpu_cycles_saved': cpu_cycles_saved
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed DMA status"""
        base_status = super().get_status()
        base_status.update({
            'channels': self.channels,
            'max_burst': self.max_burst_bytes,
            'scatter_gather': self.scatter_gather,
            'total_transferred_mb': self._total_bytes_transferred / (1024*1024)
        })
        return base_status
