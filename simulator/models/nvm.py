"""NVM (Non-Volatile Memory) and NVDIMM model"""
from typing import Dict, Any, Optional
from ..base import Module


class NVM(Module):
    """
    Non-Volatile Memory model (NVDIMM, Intel Optane, etc.).
    
    Characteristics:
    - Persistence: data survives power loss
    - Asymmetric read/write latency
    - Write endurance considerations
    """
    
    def __init__(
        self,
        name: str = "NVM",
        technology: str = "3DXPoint",  # 3DXPoint, NAND, ReRAM, STT-MRAM
        capacity_gb: int = 256,
        read_latency_ns: float = 300,
        write_latency_ns: float = 1000,
        read_bandwidth_gbps: float = 6.0,
        write_bandwidth_gbps: float = 2.5,
        endurance_cycles: int = 100000000,  # Write cycles before wear-out
        **kwargs
    ):
        super().__init__(name, **kwargs)
        
        self.technology = technology
        self.capacity_gb = capacity_gb
        self.read_latency_ns = read_latency_ns
        self.write_latency_ns = write_latency_ns
        self.read_bandwidth_gbps = read_bandwidth_gbps
        self.write_bandwidth_gbps = write_bandwidth_gbps
        self.endurance_cycles = endurance_cycles
        
        # Wear tracking
        self._total_writes = 0
        self._reads = 0
        
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """Simulate NVM access"""
        self.metrics.total_requests += 1
        
        if request_type == 'write':
            self._total_writes += 1
            base_latency = self.write_latency_ns
            bandwidth = self.write_bandwidth_gbps
        else:
            self._reads += 1
            base_latency = self.read_latency_ns
            bandwidth = self.read_bandwidth_gbps
        
        # Transfer time
        transfer_ns = (size_bytes / (bandwidth * 1e9)) * 1e9
        total_latency = base_latency + transfer_ns
        
        self.metrics.total_latency_ns += total_latency
        return total_latency
    
    def get_bandwidth(self) -> float:
        """Return average bandwidth (geometric mean of read/write)"""
        return (self.read_bandwidth_gbps * self.write_bandwidth_gbps) ** 0.5
    
    def get_power(self) -> float:
        """Return power consumption in Watts"""
        # NVM typically 10-15W active
        base_power = 12.0
        if self.technology == 'NAND':
            base_power = 8.0
        return base_power
    
    def get_wear_percentage(self) -> float:
        """Calculate wear level as percentage of endurance"""
        return (self._total_writes / self.endurance_cycles) * 100
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed NVM status"""
        base_status = super().get_status()
        base_status.update({
            'technology': self.technology,
            'capacity_gb': self.capacity_gb,
            'read_latency_ns': self.read_latency_ns,
            'write_latency_ns': self.write_latency_ns,
            'total_writes': self._total_writes,
            'wear_percentage': self.get_wear_percentage()
        })
        return base_status
