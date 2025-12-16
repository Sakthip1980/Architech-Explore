"""PCIe Link model"""
from typing import Dict, Any, Optional
from ..base import Module


class PCIe(Module):
    """
    PCI Express Link model.
    
    Features:
    - Generation-specific data rates
    - Lane configuration
    - Protocol overhead modeling
    """
    
    def __init__(
        self,
        name: str = "PCIe",
        generation: int = 4,  # 3, 4, 5, 6
        lanes: int = 16,  # x1, x4, x8, x16
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.generation = generation
        self.lanes = lanes
        
        # Data rate per lane in GT/s (Giga Transfers per second)
        self._gen_rates = {
            3: 8.0,
            4: 16.0,
            5: 32.0,
            6: 64.0
        }
        
        # Encoding efficiency
        self._encoding_efficiency = {
            3: 128/130,  # 128b/130b
            4: 128/130,
            5: 128/130,
            6: 242/256   # FLIT mode
        }
        
        # Base latency (ns) - protocol overhead
        self._base_latency = {
            3: 700,
            4: 500,
            5: 400,
            6: 300
        }
        
    def get_raw_bandwidth(self) -> float:
        """Get raw bandwidth in GB/s before encoding overhead"""
        rate_gtps = self._gen_rates.get(self.generation, 16.0)
        # GT/s to GB/s: divide by 8 (bits to bytes)
        return (rate_gtps * self.lanes) / 8
    
    def get_bandwidth(self) -> float:
        """Get effective bandwidth accounting for encoding"""
        raw_bw = self.get_raw_bandwidth()
        efficiency = self._encoding_efficiency.get(self.generation, 0.985)
        return raw_bw * efficiency
    
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate PCIe transaction"""
        self.metrics.total_requests += 1
        
        # Base latency for link establishment
        base_latency = self._base_latency.get(self.generation, 500)
        
        # Transfer time
        bandwidth_gbps = self.get_bandwidth()
        transfer_ns = (size_bytes / (bandwidth_gbps * 1e9)) * 1e9
        
        # TLP (Transaction Layer Packet) overhead
        # ~24 bytes header per 4KB payload typical
        tlp_overhead = (size_bytes / 4096) * 24
        overhead_ns = (tlp_overhead / (bandwidth_gbps * 1e9)) * 1e9
        
        total_latency = base_latency + transfer_ns + overhead_ns
        self.metrics.total_latency_ns += total_latency
        
        return total_latency
    
    def get_power(self) -> float:
        """Return estimated power in Watts"""
        # PCIe power scales with generation and lanes
        power_per_lane_w = {
            3: 0.3,
            4: 0.4,
            5: 0.6,
            6: 0.8
        }
        return power_per_lane_w.get(self.generation, 0.4) * self.lanes
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed PCIe status"""
        base_status = super().get_status()
        base_status.update({
            'generation': f'Gen{self.generation}',
            'lanes': f'x{self.lanes}',
            'raw_bandwidth_gbps': self.get_raw_bandwidth(),
            'effective_bandwidth_gbps': self.get_bandwidth()
        })
        return base_status
