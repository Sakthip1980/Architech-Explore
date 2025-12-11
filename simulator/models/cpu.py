"""CPU Core model"""
from ..base import Module


class CPU(Module):
    """Simple CPU core model"""
    
    def __init__(
        self,
        name: str = "CPU",
        frequency_ghz: float = 3.0,
        cores: int = 4,
        l1_cache_kb: int = 64,
        l2_cache_kb: int = 512,
        tdp_watts: float = 65,
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.frequency_ghz = frequency_ghz
        self.cores = cores
        self.l1_cache_kb = l1_cache_kb
        self.l2_cache_kb = l2_cache_kb
        self.tdp_watts = tdp_watts
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate CPU operation"""
        self.metrics.total_requests += 1
        
        # Simple latency model based on cache
        if size_bytes <= self.l1_cache_kb * 1024:
            latency_ns = 4 / self.frequency_ghz  # ~4 cycles for L1
        elif size_bytes <= self.l2_cache_kb * 1024:
            latency_ns = 12 / self.frequency_ghz  # ~12 cycles for L2
        else:
            latency_ns = 100  # Miss, go to DRAM
            
        self.metrics.total_latency_ns += latency_ns
        return latency_ns
    
    def get_bandwidth(self) -> float:
        """CPU memory bandwidth (simplified)"""
        return 50.0  # 50 GB/s typical
    
    def get_power(self) -> float:
        """Return TDP"""
        return self.tdp_watts
