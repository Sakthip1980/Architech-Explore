"""GPU Accelerator model"""
from ..base import Module


class GPU(Module):
    """GPU accelerator model"""
    
    def __init__(
        self,
        name: str = "GPU",
        frequency_ghz: float = 1.5,
        compute_units: int = 20,
        memory_bandwidth_gbps: float = 256,
        tdp_watts: float = 150,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.frequency_ghz = frequency_ghz
        self.compute_units = compute_units
        self.memory_bandwidth_gbps = memory_bandwidth_gbps
        self.tdp_watts = tdp_watts
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate GPU operation"""
        self.metrics.total_requests += 1
        
        # GPU memory access latency (typically higher than CPU)
        latency_ns = 200 + (size_bytes / (self.memory_bandwidth_gbps * 1e9)) * 1e9
        
        self.metrics.total_latency_ns += latency_ns
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """Return memory bandwidth"""
        return self.memory_bandwidth_gbps
    
    def get_power(self) -> float:
        """Return TDP"""
        return self.tdp_watts
