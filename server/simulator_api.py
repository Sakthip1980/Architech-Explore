"""API wrapper for the simulator backend"""
from typing import Dict, Any, List
import sys
import os

# Add simulator to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simulator import System, DRAM, CPU, GPU, Interconnect


class SimulatorAPI:
    """Interface between Express API and Python simulator"""
    
    def __init__(self):
        self.system: System | None = None
        
    def build_system_from_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a system from frontend graph representation
        
        Args:
            graph_data: Dictionary with 'nodes' and 'edges' from React Flow
            
        Returns:
            System topology information
        """
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Create new system
        self.system = System(name='UserArchitecture')
        module_map = {}
        
        # Create modules from nodes
        for node in nodes:
            node_id = node['id']
            data = node['data']
            label = data.get('label', 'Unknown')
            
            # Instantiate appropriate module type
            if label == 'DRAM Controller':
                module = DRAM(
                    name=f"DRAM_{node_id}",
                    frequency_mhz=int(float(data.get('frequency', 2.4)) * 1000),
                    timings={
                        'tCL': int(data.get('tCL', 16)),
                        'tRCD': int(data.get('tRCD', 18)),
                        'tRP': int(data.get('tRP', 18)),
                        'tRAS': int(data.get('tRAS', 36))
                    },
                    geometry={
                        'banks': int(data.get('banks', 16)),
                        'bus_width': int(data.get('busWidth', 64)),
                        'ranks': 2
                    }
                )
            elif label == 'CPU Core':
                module = CPU(
                    name=f"CPU_{node_id}",
                    frequency_ghz=float(data.get('frequency', 3.0)),
                    tdp_watts=float(data.get('power', 65))
                )
            elif label == 'GPU Accelerator':
                module = GPU(
                    name=f"GPU_{node_id}",
                    frequency_ghz=float(data.get('frequency', 1.5)),
                    memory_bandwidth_gbps=float(data.get('bandwidth', 256)),
                    tdp_watts=float(data.get('power', 150))
                )
            elif 'NoC' in label or 'Bus' in label:
                module = Interconnect(
                    name=f"Interconnect_{node_id}",
                    bandwidth_gbps=float(data.get('bandwidth', 100)),
                    latency_ns=float(data.get('latency', 10))
                )
            else:
                # Generic module
                module = CPU(name=f"Module_{node_id}")
            
            self.system.add_module(module)
            module_map[node_id] = module
        
        # Create connections from edges
        for edge in edges:
            source_id = edge['source']
            target_id = edge['target']
            
            if source_id in module_map and target_id in module_map:
                self.system.connect(module_map[source_id], module_map[target_id])
        
        return self.system.get_topology()
    
    def run_simulation(
        self,
        cycles: int = 1000,
        workload: str = 'memory_intensive'
    ) -> Dict[str, Any]:
        """
        Run simulation on the current system
        
        Args:
            cycles: Number of cycles to simulate
            workload: Workload type
            
        Returns:
            Simulation results
        """
        if not self.system:
            return {'error': 'No system built. Build a system first.'}
        
        results = self.system.simulate(cycles=cycles, workload=workload)
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.system:
            return {'error': 'No system built'}
        
        return self.system.get_topology()


# Global simulator instance
simulator = SimulatorAPI()
