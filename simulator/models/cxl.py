"""CXL (Compute Express Link) Interface model"""
from typing import Dict, Any, Optional
from ..base import Module


class CXL(Module):
    """
    CXL (Compute Express Link) Interface model.
    
    CXL enables:
    - Cache-coherent memory expansion
    - Device-attached memory
    - Heterogeneous computing
    
    CXL Types:
    - Type 1: I/O devices (accelerators)
    - Type 2: Accelerators with device-attached memory
    - Type 3: Memory expansion
    """
    
    def __init__(
        self,
        name: str = "CXL",
        version: str = "2.0",  # 1.1, 2.0, 3.0
        cxl_type: int = 3,  # 1, 2, or 3
        lanes: int = 16,
        attached_memory_gb: int = 128,
        cache_coherent: bool = True,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.version = version
        self.cxl_type = cxl_type
        self.lanes = lanes
        self.attached_memory_gb = attached_memory_gb
        self.cache_coherent = cache_coherent
        
        # CXL version bandwidth (based on PCIe)
        self._version_bandwidth = {
            '1.1': 32.0,   # PCIe 5.0 x16
            '2.0': 32.0,
            '3.0': 64.0    # PCIe 6.0 x16
        }
        
        # CXL latency overhead (ns) on top of memory access
        self._cxl_overhead = {
            '1.1': 200,
            '2.0': 150,
            '3.0': 100
        }
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate CXL memory access"""
        self.metrics.total_requests += 1
        
        # Base CXL protocol overhead
        overhead = self._cxl_overhead.get(self.version, 150)
        
        # Cache coherency adds latency for Type 1/2
        if self.cache_coherent and self.cxl_type in [1, 2]:
            overhead += 50  # Snoop/coherence overhead
        
        # Memory access (assuming DDR-like backing)
        memory_latency = 80  # Base DRAM latency
        
        # Transfer over CXL link
        bandwidth = self.get_bandwidth() * (self.lanes / 16)
        transfer_ns = (size_bytes / (bandwidth * 1e9)) * 1e9
        
        total_latency = overhead + memory_latency + transfer_ns
        self.metrics.total_latency_ns += total_latency
        
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return CXL bandwidth in GB/s"""
        base_bw = self._version_bandwidth.get(self.version, 32.0)
        return base_bw * (self.lanes / 16)
    
    def get_power(self) -> float:
        """Return estimated power in Watts"""
        # CXL controller + memory power
        controller_power = 5.0
        memory_power = self.attached_memory_gb * 0.1  # ~0.1W per GB
        return controller_power + memory_power
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed CXL status"""
        base_status = super().get_status()
        base_status.update({
            'version': self.version,
            'type': f'Type {self.cxl_type}',
            'lanes': f'x{self.lanes}',
            'attached_memory_gb': self.attached_memory_gb,
            'cache_coherent': self.cache_coherent,
            'bandwidth_gbps': self.get_bandwidth()
        })
        return base_status
