import React, { useState } from 'react';
import { 
  Cpu, Database, Network, HardDrive, Zap, CircuitBoard, 
  Layers, MemoryStick, Cable, Server, Workflow, Binary,
  ChevronDown, ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModuleCategory {
  name: string;
  modules: ModuleItem[];
}

interface ModuleItem {
  type: string;
  label: string;
  icon: any;
  color: string;
  description: string;
}

const categories: ModuleCategory[] = [
  {
    name: 'Memory Subsystem',
    modules: [
      { type: 'dram', label: 'DRAM Controller', icon: Database, color: 'text-purple-400', description: 'DDR4/5 memory' },
      { type: 'hbm', label: 'HBM', icon: Layers, color: 'text-violet-400', description: 'High bandwidth 3D stacked' },
      { type: 'cache', label: 'SRAM Cache', icon: MemoryStick, color: 'text-indigo-400', description: 'L1/L2/L3 cache' },
      { type: 'nvm', label: 'NVM Storage', icon: HardDrive, color: 'text-blue-400', description: 'Non-volatile memory' },
      { type: 'scratchpad', label: 'Scratchpad', icon: Binary, color: 'text-sky-400', description: 'Software-managed SPM' },
    ]
  },
  {
    name: 'Compute Units',
    modules: [
      { type: 'cpu', label: 'CPU Core', icon: Cpu, color: 'text-cyan-400', description: 'General purpose' },
      { type: 'gpu', label: 'GPU Accelerator', icon: Zap, color: 'text-yellow-400', description: 'Parallel compute' },
      { type: 'npu', label: 'NPU', icon: CircuitBoard, color: 'text-orange-400', description: 'Neural processor' },
      { type: 'dsp', label: 'DSP', icon: Workflow, color: 'text-amber-400', description: 'Signal processing' },
      { type: 'systolic', label: 'Systolic Array', icon: Layers, color: 'text-red-400', description: 'GEMM accelerator' },
    ]
  },
  {
    name: 'Interconnects',
    modules: [
      { type: 'noc', label: 'NoC / Bus', icon: Network, color: 'text-green-400', description: 'On-chip network' },
      { type: 'axi', label: 'AXI Bus', icon: Cable, color: 'text-emerald-400', description: 'AMBA protocol' },
      { type: 'pcie', label: 'PCIe Link', icon: Cable, color: 'text-teal-400', description: 'High-speed I/O' },
      { type: 'cxl', label: 'CXL Interface', icon: Server, color: 'text-lime-400', description: 'Cache coherent' },
    ]
  },
  {
    name: 'Specialized',
    modules: [
      { type: 'dma', label: 'DMA Engine', icon: Workflow, color: 'text-pink-400', description: 'Memory transfer' },
      { type: 'memctrl', label: 'Memory Controller', icon: Server, color: 'text-rose-400', description: 'Request scheduling' },
    ]
  }
];

export const Sidebar = () => {
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['Memory Subsystem', 'Compute Units']);

  const onDragStart = (event: React.DragEvent, label: string) => {
    event.dataTransfer.setData('application/reactflow', 'custom');
    event.dataTransfer.setData('application/label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  const toggleCategory = (name: string) => {
    setExpandedCategories(prev => 
      prev.includes(name) 
        ? prev.filter(c => c !== name)
        : [...prev, name]
    );
  };

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border h-full flex flex-col z-10">
      <div className="p-4 border-b border-sidebar-border">
        <h1 className="text-xl font-bold font-mono tracking-tight text-primary">
          ArchSim<span className="text-muted-foreground text-sm">.v2</span>
        </h1>
        <p className="text-xs text-muted-foreground mt-1 font-mono">System Architecture Simulator</p>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {categories.map((category) => (
          <div key={category.name} className="mb-2">
            <button
              onClick={() => toggleCategory(category.name)}
              className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
              data-testid={`category-${category.name.toLowerCase().replace(/\s+/g, '-')}`}
            >
              {expandedCategories.includes(category.name) 
                ? <ChevronDown className="w-3 h-3" />
                : <ChevronRight className="w-3 h-3" />
              }
              {category.name}
            </button>
            
            {expandedCategories.includes(category.name) && (
              <div className="space-y-1 mt-1">
                {category.modules.map((module) => (
                  <div
                    key={module.type}
                    onDragStart={(event) => onDragStart(event, module.label)}
                    draggable
                    className="group flex items-center gap-2 px-2 py-2 rounded-md border border-transparent bg-card/30 hover:bg-sidebar-accent hover:border-primary/30 cursor-grab transition-all"
                    data-testid={`module-${module.type}`}
                  >
                    <module.icon className={cn("w-4 h-4", module.color)} />
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-medium font-mono text-sidebar-foreground truncate">
                        {module.label}
                      </span>
                      <span className="text-[9px] text-muted-foreground truncate">
                        {module.description}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-sidebar-border bg-sidebar/50">
        <div className="text-[10px] text-muted-foreground font-mono space-y-1">
          <p className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Python Backend: Connected
          </p>
          <p>Drag components to canvas</p>
        </div>
      </div>
    </aside>
  );
};
