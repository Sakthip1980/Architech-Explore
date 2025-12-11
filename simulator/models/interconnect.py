"""Interconnect models (NoC, AXI Bus, etc.)"""
from ..base import Module


class Interconnect(Module):
    """Network-on-Chip or Bus interconnect model"""
    
    def __init__(
        self,
        name: str = "Interconnect",
        bandwidth_gbps: float = 100,
        latency_ns: float = 10,
        topology: str = "mesh",
        **kwargs
    ):
        super().__init__(name, **kwargs)
        self.bandwidth_gbps = bandwidth_gbps
        self.latency_ns = latency_ns
        self.topology = topology
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate interconnect transfer"""
        self.metrics.total_requests += 1
        
        # Base latency + transfer time
        transfer_time_ns = (size_bytes / (self.bandwidth_gbps * 1e9)) * 1e9
        total_latency = self.latency_ns + transfer_time_ns
        
        self.metrics.total_latency_ns += total_latency
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return interconnect bandwidth"""
        return self.bandwidth_gbps
    
    def get_power(self) -> float:
        """Return power consumption"""
        return 5.0  # Fixed 5W for interconnect
