"""API wrapper for the simulator backend"""
from typing import Dict, Any, List, Optional
import sys
import os
import json

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from simulator import (
    System, 
    # Memory
    DRAM, HBM, SRAMCache, NVM, Scratchpad,
    # Compute
    CPU, GPU, NPU, DSP,
    # Interconnects
    Interconnect, AXIBus, PCIe, CXL,
    # Specialized
    DMAEngine, MemoryController
)

# State file for persistence between calls
STATE_FILE = os.path.join(project_root, '.simulator_state.json')


def safe_int(value: Any, default: int) -> int:
    """Safely convert value to int"""
    try:
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float) -> float:
    """Safely convert value to float"""
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return default


class SimulatorAPI:
    """Interface between Express API and Python simulator"""
    
    def __init__(self):
        self.system: Optional[System] = None
        self._graph_data: Optional[Dict] = None
        
    def _save_state(self, graph_data: Dict):
        """Save graph data to file for persistence"""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(graph_data, f)
        except Exception:
            pass
    
    def _load_state(self) -> Optional[Dict]:
        """Load graph data from file"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    def _create_module(self, node_id: str, data: Dict) -> Any:
        """Create appropriate module based on label with safe parameter handling"""
        label = data.get('label', 'Unknown')
        
        # Memory Subsystem
        if label == 'DRAM Controller':
            return DRAM(
                name=f"DRAM_{node_id}",
                frequency_mhz=safe_int(safe_float(data.get('frequency', 2.4), 2.4) * 1000, 2400),
                timings={
                    'tCL': safe_int(data.get('tCL', 16), 16),
                    'tRCD': safe_int(data.get('tRCD', 18), 18),
                    'tRP': safe_int(data.get('tRP', 18), 18),
                    'tRAS': safe_int(data.get('tRAS', 36), 36)
                },
                geometry={
                    'banks': safe_int(data.get('banks', 16), 16),
                    'bus_width': safe_int(data.get('busWidth', 64), 64),
                    'ranks': 2
                }
            )
        elif label == 'HBM':
            return HBM(
                name=f"HBM_{node_id}",
                generation=str(data.get('generation', 'HBM2e')),
                stacks=safe_int(data.get('stacks', 4), 4),
                capacity_per_stack_gb=safe_int(data.get('capacityPerStack', 4), 4),
                frequency_gbps=safe_float(data.get('frequency', 2.4), 2.4)
            )
        elif label == 'SRAM Cache':
            return SRAMCache(
                name=f"Cache_{node_id}",
                level=safe_int(data.get('level', 2), 2),
                size_kb=safe_int(data.get('sizeKb', 256), 256),
                associativity=safe_int(data.get('associativity', 8), 8),
                frequency_ghz=safe_float(data.get('frequency', 3.0), 3.0)
            )
        elif label == 'NVM Storage':
            return NVM(
                name=f"NVM_{node_id}",
                technology=str(data.get('technology', '3DXPoint')),
                capacity_gb=safe_int(data.get('capacityGb', 256), 256),
                read_latency_ns=safe_float(data.get('readLatency', 300), 300),
                write_latency_ns=safe_float(data.get('writeLatency', 1000), 1000)
            )
        elif label == 'Scratchpad':
            return Scratchpad(
                name=f"SPM_{node_id}",
                size_kb=safe_int(data.get('sizeKb', 256), 256),
                partitions=safe_int(data.get('partitions', 4), 4),
                frequency_ghz=safe_float(data.get('frequency', 1.0), 1.0)
            )
        
        # Compute Units
        elif label == 'CPU Core':
            return CPU(
                name=f"CPU_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 3.0), 3.0),
                cores=safe_int(data.get('cores', 4), 4),
                tdp_watts=safe_float(data.get('power', 65), 65)
            )
        elif label == 'GPU Accelerator':
            return GPU(
                name=f"GPU_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 1.5), 1.5),
                memory_bandwidth_gbps=safe_float(data.get('bandwidth', 256), 256),
                tdp_watts=safe_float(data.get('power', 150), 150)
            )
        elif label == 'NPU':
            return NPU(
                name=f"NPU_{node_id}",
                mac_units=safe_int(data.get('macUnits', 4096), 4096),
                frequency_ghz=safe_float(data.get('frequency', 1.0), 1.0),
                precision=str(data.get('precision', 'INT8')),
                on_chip_sram_mb=safe_int(data.get('sramMb', 32), 32),
                tdp_watts=safe_float(data.get('power', 30), 30)
            )
        elif label == 'DSP':
            return DSP(
                name=f"DSP_{node_id}",
                frequency_ghz=safe_float(data.get('frequency', 1.2), 1.2),
                vector_width=safe_int(data.get('vectorWidth', 256), 256),
                tdp_watts=safe_float(data.get('power', 5), 5)
            )
        
        # Interconnects
        elif label == 'NoC / Bus':
            return Interconnect(
                name=f"Interconnect_{node_id}",
                bandwidth_gbps=safe_float(data.get('bandwidth', 100), 100),
                latency_ns=safe_float(data.get('latency', 10), 10)
            )
        elif label == 'AXI Bus':
            return AXIBus(
                name=f"AXI_{node_id}",
                version=str(data.get('version', 'AXI4')),
                data_width_bits=safe_int(data.get('dataWidth', 128), 128),
                frequency_mhz=safe_float(data.get('frequencyMhz', 200), 200)
            )
        elif label == 'PCIe Link':
            return PCIe(
                name=f"PCIe_{node_id}",
                generation=safe_int(data.get('generation', 4), 4),
                lanes=safe_int(data.get('lanes', 16), 16)
            )
        elif label == 'CXL Interface':
            return CXL(
                name=f"CXL_{node_id}",
                version=str(data.get('version', '2.0')),
                cxl_type=safe_int(data.get('cxlType', 3), 3),
                lanes=safe_int(data.get('lanes', 16), 16),
                attached_memory_gb=safe_int(data.get('memoryGb', 128), 128)
            )
        
        # Specialized
        elif label == 'DMA Engine':
            return DMAEngine(
                name=f"DMA_{node_id}",
                channels=safe_int(data.get('channels', 8), 8),
                bandwidth_gbps=safe_float(data.get('bandwidth', 25.6), 25.6)
            )
        elif label == 'Memory Controller':
            return MemoryController(
                name=f"MemCtrl_{node_id}",
                scheduling_policy=str(data.get('policy', 'FR-FCFS')),
                channels=safe_int(data.get('channels', 2), 2)
            )
        
        # Default fallback
        else:
            return CPU(name=f"Module_{node_id}")
        
    def build_system_from_graph(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build a system from frontend graph representation"""
        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        
        # Save state for later
        self._save_state(graph_data)
        self._graph_data = graph_data
        
        # Create new system
        self.system = System(name='UserArchitecture')
        module_map = {}
        
        # Create modules from nodes
        for node in nodes:
            node_id = node['id']
            data = node.get('data', {})
            
            module = self._create_module(node_id, data)
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
        """Run simulation on the current system"""
        if not self.system:
            saved_state = self._load_state()
            if saved_state:
                self.build_system_from_graph(saved_state)
        
        if not self.system:
            return {'error': 'No system built. Build a system first.'}
        
        results = self.system.simulate(cycles=cycles, workload=workload)
        return results
    
    def build_and_run(
        self,
        graph_data: Dict[str, Any],
        cycles: int = 1000,
        workload: str = 'memory_intensive'
    ) -> Dict[str, Any]:
        """Build system and run simulation in one call"""
        topology = self.build_system_from_graph(graph_data)
        results = self.run_simulation(cycles=cycles, workload=workload)
        return {
            'topology': topology,
            'simulation': results
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        if not self.system:
            saved_state = self._load_state()
            if saved_state:
                self.build_system_from_graph(saved_state)
                
        if not self.system:
            return {'error': 'No system built'}
        
        return self.system.get_topology()


# Global simulator instance
simulator = SimulatorAPI()
