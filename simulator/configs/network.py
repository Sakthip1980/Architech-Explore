"""Network topology and collective communication configuration"""
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum
import math


class NetworkTopology(Enum):
    RING = "ring"
    SWITCH = "switch"
    FULLY_CONNECTED = "fc"
    TORUS_2D = "2d_torus"
    TORUS_3D = "3d_torus"
    TREE = "tree"


class CollectiveAlgorithm(Enum):
    AUTO = "auto"
    RING = "ring"
    DIRECT = "direct"
    HALVING_DOUBLING = "halvingDoubling"
    DOUBLE_BINARY_TREE = "doubleBinaryTree"
    RECURSIVE_HALVING = "recursiveHalving"


class CollectiveType(Enum):
    ALL_REDUCE = "all_reduce"
    ALL_GATHER = "all_gather"
    REDUCE_SCATTER = "reduce_scatter"
    ALL_TO_ALL = "all_to_all"
    BROADCAST = "broadcast"
    REDUCE = "reduce"


@dataclass
class CollectiveConfig:
    """Configuration for collective communication operations"""
    all_reduce: CollectiveAlgorithm = CollectiveAlgorithm.AUTO
    all_gather: CollectiveAlgorithm = CollectiveAlgorithm.AUTO
    reduce_scatter: CollectiveAlgorithm = CollectiveAlgorithm.AUTO
    all_to_all: CollectiveAlgorithm = CollectiveAlgorithm.AUTO
    
    def get_algorithm(self, collective_type: CollectiveType) -> CollectiveAlgorithm:
        """Get algorithm for a specific collective type"""
        mapping = {
            CollectiveType.ALL_REDUCE: self.all_reduce,
            CollectiveType.ALL_GATHER: self.all_gather,
            CollectiveType.REDUCE_SCATTER: self.reduce_scatter,
            CollectiveType.ALL_TO_ALL: self.all_to_all,
        }
        return mapping.get(collective_type, CollectiveAlgorithm.AUTO)


@dataclass
class NetworkConfig:
    """Network configuration matching Astra-Sim schema"""
    topology: NetworkTopology = NetworkTopology.RING
    npus_count: int = 8
    bandwidth_gbps: float = 400.0
    latency_ns: float = 1000.0
    
    # Multi-dimensional topology (for 2D/3D torus)
    dimensions: List[int] = field(default_factory=lambda: [8])
    
    # Collective configuration
    collectives: CollectiveConfig = field(default_factory=CollectiveConfig)
    
    # System options
    endpoint_delay_ns: int = 10
    active_chunks_per_dimension: int = 32
    
    def get_bisection_bandwidth(self) -> float:
        """Calculate bisection bandwidth for the topology"""
        n = self.npus_count
        bw = self.bandwidth_gbps
        
        if self.topology == NetworkTopology.RING:
            return 2 * bw  # Two links at bisection
        elif self.topology == NetworkTopology.SWITCH:
            return n * bw / 2  # Full bisection
        elif self.topology == NetworkTopology.FULLY_CONNECTED:
            return n * bw / 2
        elif self.topology == NetworkTopology.TORUS_2D:
            dim = int(math.sqrt(n))
            return 2 * dim * bw
        return n * bw / 2
    
    def estimate_collective_time_ns(
        self,
        collective_type: CollectiveType,
        message_size_bytes: int,
        num_participants: int
    ) -> float:
        """Estimate time for a collective operation"""
        n = num_participants
        size_bytes = message_size_bytes
        bw_bytes_per_ns = self.bandwidth_gbps * 1e9 / 8 / 1e9  # GB/s to B/ns
        
        algorithm = self.collectives.get_algorithm(collective_type)
        
        # Default to ring if auto
        if algorithm == CollectiveAlgorithm.AUTO:
            if n <= 8:
                algorithm = CollectiveAlgorithm.RING
            else:
                algorithm = CollectiveAlgorithm.HALVING_DOUBLING
        
        if algorithm == CollectiveAlgorithm.RING:
            # Ring: 2*(n-1)/n * size / bandwidth
            if collective_type == CollectiveType.ALL_REDUCE:
                data_factor = 2 * (n - 1) / n
            elif collective_type == CollectiveType.ALL_GATHER:
                data_factor = (n - 1) / n
            elif collective_type == CollectiveType.REDUCE_SCATTER:
                data_factor = (n - 1) / n
            else:  # ALL_TO_ALL
                data_factor = (n - 1) / n
            
            transfer_time = (size_bytes * data_factor) / (bw_bytes_per_ns + 1e-10)
            latency_time = (n - 1) * self.latency_ns
            
        elif algorithm == CollectiveAlgorithm.HALVING_DOUBLING:
            # Halving-Doubling: log2(n) steps
            steps = int(math.ceil(math.log2(n)))
            
            if collective_type == CollectiveType.ALL_REDUCE:
                data_factor = 2 * (n - 1) / n
            else:
                data_factor = (n - 1) / n
            
            transfer_time = (size_bytes * data_factor) / (bw_bytes_per_ns + 1e-10)
            latency_time = steps * 2 * self.latency_ns
            
        elif algorithm == CollectiveAlgorithm.DOUBLE_BINARY_TREE:
            # DBT: 2*log2(n) steps, but pipelined
            steps = int(math.ceil(math.log2(n)))
            
            if collective_type == CollectiveType.ALL_REDUCE:
                data_factor = 2 * (n - 1) / n
            else:
                data_factor = (n - 1) / n
            
            transfer_time = (size_bytes * data_factor) / (bw_bytes_per_ns + 1e-10)
            latency_time = 2 * steps * self.latency_ns
            
        else:  # DIRECT
            # Direct: all-pairs
            transfer_time = (size_bytes * (n - 1)) / (bw_bytes_per_ns + 1e-10)
            latency_time = self.latency_ns
        
        return transfer_time + latency_time + self.endpoint_delay_ns
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'topology': self.topology.value,
            'npus_count': self.npus_count,
            'bandwidth_gbps': self.bandwidth_gbps,
            'latency_ns': self.latency_ns,
            'bisection_bandwidth_gbps': self.get_bisection_bandwidth(),
            'dimensions': self.dimensions,
            'collectives': {
                'all_reduce': self.collectives.all_reduce.value,
                'all_gather': self.collectives.all_gather.value,
                'reduce_scatter': self.collectives.reduce_scatter.value,
                'all_to_all': self.collectives.all_to_all.value,
            },
        }


# Network configuration presets (based on Astra-Sim)
NETWORK_PRESETS: Dict[str, NetworkConfig] = {
    'dgx_v100_8gpu': NetworkConfig(
        topology=NetworkTopology.SWITCH,
        npus_count=8,
        bandwidth_gbps=300,
        latency_ns=5000,
    ),
    'hgx_h100_8gpu': NetworkConfig(
        topology=NetworkTopology.SWITCH,
        npus_count=8,
        bandwidth_gbps=400,
        latency_ns=936,
    ),
    'hgx_h100_16gpu': NetworkConfig(
        topology=NetworkTopology.SWITCH,
        npus_count=16,
        bandwidth_gbps=400,
        latency_ns=1000,
    ),
    'hgx_h100_32gpu': NetworkConfig(
        topology=NetworkTopology.SWITCH,
        npus_count=32,
        bandwidth_gbps=400,
        latency_ns=1500,
    ),
    'tpu_v3_8': NetworkConfig(
        topology=NetworkTopology.RING,
        npus_count=8,
        bandwidth_gbps=656,
        latency_ns=1000,
    ),
    'tpu_v3_32_ring': NetworkConfig(
        topology=NetworkTopology.RING,
        npus_count=32,
        bandwidth_gbps=656,
        latency_ns=2000,
    ),
    'tpu_v3_32_torus': NetworkConfig(
        topology=NetworkTopology.TORUS_2D,
        npus_count=32,
        bandwidth_gbps=656,
        latency_ns=1500,
        dimensions=[8, 4],
    ),
}
