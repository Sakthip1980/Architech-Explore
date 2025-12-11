"""Base classes for all simulation modules"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class SimulationMetrics:
    """Track simulation performance metrics"""
    total_cycles: int = 0
    total_requests: int = 0
    total_latency_ns: float = 0.0
    power_consumed_mw: float = 0.0
    bandwidth_utilized_gbps: float = 0.0
    
    def average_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ns / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_cycles': self.total_cycles,
            'total_requests': self.total_requests,
            'avg_latency_ns': self.average_latency(),
            'power_consumed_mw': self.power_consumed_mw,
            'bandwidth_utilized_gbps': self.bandwidth_utilized_gbps
        }


class Module(ABC):
    """Base class for all hardware modules in the system"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.id = id(self)
        self.connections: Dict[str, 'Module'] = {}
        self.metrics = SimulationMetrics()
        self._config = kwargs
        
    @abstractmethod
    def process_request(self, request_type: str, size_bytes: int) -> float:
        """
        Process a request and return latency in nanoseconds
        
        Args:
            request_type: Type of request (read, write, compute, etc.)
            size_bytes: Size of data being transferred
            
        Returns:
            Latency in nanoseconds
        """
        pass
    
    @abstractmethod
    def get_bandwidth(self) -> float:
        """Return available bandwidth in GB/s"""
        pass
    
    @abstractmethod
    def get_power(self) -> float:
        """Return current power consumption in Watts"""
        pass
    
    def connect(self, other: 'Module', name: Optional[str] = None):
        """Create a connection to another module"""
        connection_name = name or other.name
        self.connections[connection_name] = other
        
    def get_status(self) -> Dict[str, Any]:
        """Get current module status"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'metrics': self.metrics.to_dict(),
            'bandwidth_gbps': self.get_bandwidth(),
            'power_watts': self.get_power(),
            'connections': list(self.connections.keys())
        }
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.metrics = SimulationMetrics()
