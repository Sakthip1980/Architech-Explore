import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { 
  Cpu, Database, Network, HardDrive, Zap, CircuitBoard,
  Layers, MemoryStick, Cable, Server, Workflow, Binary, GripHorizontal,
  Activity, AlertTriangle
} from 'lucide-react';
import { clsx } from 'clsx';

const icons: Record<string, any> = {
  'CPU Core': Cpu,
  'GPU Accelerator': Zap,
  'DRAM Controller': Database,
  'NVM Storage': HardDrive,
  'NoC / Bus': Network,
  'Custom Logic': CircuitBoard,
  'HBM': Layers,
  'SRAM Cache': MemoryStick,
  'Scratchpad': Binary,
  'NPU': CircuitBoard,
  'DSP': Workflow,
  'AXI Bus': Cable,
  'PCIe Link': Cable,
  'CXL Interface': Server,
  'DMA Engine': Workflow,
  'Memory Controller': Server,
  'Systolic Array': Layers,
};

const colors: Record<string, string> = {
  'CPU Core': 'border-cyan-500 shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)]',
  'GPU Accelerator': 'border-yellow-500 shadow-[0_0_15px_-3px_rgba(234,179,8,0.3)]',
  'DRAM Controller': 'border-purple-500 shadow-[0_0_15px_-3px_rgba(168,85,247,0.3)]',
  'NVM Storage': 'border-blue-500 shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)]',
  'NoC / Bus': 'border-green-500 shadow-[0_0_15px_-3px_rgba(34,197,94,0.3)]',
  'Custom Logic': 'border-pink-500 shadow-[0_0_15px_-3px_rgba(236,72,153,0.3)]',
  'HBM': 'border-violet-500 shadow-[0_0_15px_-3px_rgba(139,92,246,0.3)]',
  'SRAM Cache': 'border-indigo-500 shadow-[0_0_15px_-3px_rgba(99,102,241,0.3)]',
  'Scratchpad': 'border-sky-500 shadow-[0_0_15px_-3px_rgba(14,165,233,0.3)]',
  'NPU': 'border-orange-500 shadow-[0_0_15px_-3px_rgba(249,115,22,0.3)]',
  'DSP': 'border-amber-500 shadow-[0_0_15px_-3px_rgba(245,158,11,0.3)]',
  'AXI Bus': 'border-emerald-500 shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]',
  'PCIe Link': 'border-teal-500 shadow-[0_0_15px_-3px_rgba(20,184,166,0.3)]',
  'CXL Interface': 'border-lime-500 shadow-[0_0_15px_-3px_rgba(132,204,22,0.3)]',
  'DMA Engine': 'border-pink-500 shadow-[0_0_15px_-3px_rgba(236,72,153,0.3)]',
  'Memory Controller': 'border-rose-500 shadow-[0_0_15px_-3px_rgba(244,63,94,0.3)]',
  'Systolic Array': 'border-red-500 shadow-[0_0_15px_-3px_rgba(239,68,68,0.3)]',
};

const textColors: Record<string, string> = {
  'CPU Core': 'text-cyan-500',
  'GPU Accelerator': 'text-yellow-500',
  'DRAM Controller': 'text-purple-500',
  'NVM Storage': 'text-blue-500',
  'NoC / Bus': 'text-green-500',
  'Custom Logic': 'text-pink-500',
  'HBM': 'text-violet-500',
  'SRAM Cache': 'text-indigo-500',
  'Scratchpad': 'text-sky-500',
  'NPU': 'text-orange-500',
  'DSP': 'text-amber-500',
  'AXI Bus': 'text-emerald-500',
  'PCIe Link': 'text-teal-500',
  'CXL Interface': 'text-lime-500',
  'DMA Engine': 'text-pink-500',
  'Memory Controller': 'text-rose-500',
  'Systolic Array': 'text-red-500',
};

const getMetricLabels = (label: string): { primary: string; secondary: string } => {
  switch (label) {
    case 'HBM':
      return { primary: 'Stacks', secondary: 'Gen' };
    case 'SRAM Cache':
      return { primary: 'Size', secondary: 'Level' };
    case 'NPU':
      return { primary: 'MACs', secondary: 'Precision' };
    case 'PCIe Link':
      return { primary: 'Gen', secondary: 'Lanes' };
    case 'CXL Interface':
      return { primary: 'Type', secondary: 'Ver' };
    case 'Systolic Array':
      return { primary: 'Array', secondary: 'Dataflow' };
    default:
      return { primary: 'BW', secondary: 'LAT' };
  }
};

const getMetricValues = (data: any): { primary: string; secondary: string } => {
  const label = data.label;
  switch (label) {
    case 'HBM':
      return { primary: `${data.stacks || 4}`, secondary: data.generation || 'HBM2e' };
    case 'SRAM Cache':
      return { primary: `${data.sizeKb || 256}KB`, secondary: `L${data.level || 2}` };
    case 'NPU':
      return { primary: `${data.macUnits || 4096}`, secondary: data.precision || 'INT8' };
    case 'PCIe Link':
      return { primary: `${data.generation || 4}`, secondary: `x${data.lanes || 16}` };
    case 'CXL Interface':
      return { primary: `${data.cxlType || 3}`, secondary: data.version || '2.0' };
    case 'Systolic Array':
      return { primary: `${data.arrayHeight || 256}x${data.arrayWidth || 256}`, secondary: data.dataflow || 'OS' };
    default:
      return { primary: `${data.bandwidth || '100'} GB/s`, secondary: `${data.latency || '10'} ns` };
  }
};

const getUtilizationColor = (u: number) => {
  if (u >= 80) return 'text-green-500 bg-green-500/20';
  if (u >= 50) return 'text-yellow-500 bg-yellow-500/20';
  return 'text-red-500 bg-red-500/20';
};

export const CustomNode = memo(({ data, selected }: NodeProps) => {
  const Icon = icons[data.label as string] || CircuitBoard;
  const borderColor = colors[data.label as string] || 'border-border';
  const textColor = textColors[data.label as string] || 'text-foreground';
  const metricLabels = getMetricLabels(data.label);
  const metricValues = getMetricValues(data);
  
  const hasKPIs = data.kpiUtilization !== undefined || data.kpiPower !== undefined;
  const isBottleneck = data.isBottleneck;

  return (
    <div className={clsx(
      "px-4 py-3 min-w-[180px] rounded-md bg-card border-2 transition-all duration-200",
      selected ? borderColor : "border-border hover:border-border/80",
      isBottleneck && "ring-2 ring-red-500/50 animate-pulse",
      "group relative"
    )}>
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground !w-2 !h-4 !rounded-sm !-left-[10px]" />
      <Handle type="target" position={Position.Top} className="!bg-muted-foreground !w-4 !h-2 !rounded-sm !-top-[10px]" />
      
      <div className="flex items-center gap-3 mb-2">
        <div className={clsx("p-1.5 rounded bg-background/50", textColor)}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-mono text-xs font-bold text-foreground">{data.label}</span>
          <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">{data.frequency || '2.0'} GHz</span>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-[9px] font-mono text-muted-foreground">
          <span>{metricLabels.primary}:</span>
          <span className="text-foreground">{metricValues.primary}</span>
        </div>
        <div className="flex justify-between text-[9px] font-mono text-muted-foreground">
          <span>{metricLabels.secondary}:</span>
          <span className="text-foreground">{metricValues.secondary}</span>
        </div>
      </div>

      {hasKPIs && (
        <div className="mt-2 pt-2 border-t border-border/50 space-y-1">
          {data.kpiUtilization !== undefined && (
            <div className={clsx(
              "flex items-center justify-between text-[9px] font-mono px-1.5 py-0.5 rounded",
              getUtilizationColor(data.kpiUtilization)
            )}>
              <span className="flex items-center gap-1">
                <Activity className="w-2.5 h-2.5" />
                Util:
              </span>
              <span className="font-bold">{data.kpiUtilization.toFixed(1)}%</span>
            </div>
          )}
          {data.kpiPower !== undefined && (
            <div className="flex items-center justify-between text-[9px] font-mono px-1.5 py-0.5 rounded text-orange-500 bg-orange-500/20">
              <span className="flex items-center gap-1">
                <Zap className="w-2.5 h-2.5" />
                Power:
              </span>
              <span className="font-bold">{data.kpiPower.toFixed(1)}W</span>
            </div>
          )}
          {isBottleneck && (
            <div className="flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded text-red-500 bg-red-500/20">
              <AlertTriangle className="w-2.5 h-2.5" />
              <span className="font-bold">Bottleneck</span>
            </div>
          )}
        </div>
      )}

      <div className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <GripHorizontal className="w-4 h-4 text-muted-foreground/50" />
      </div>

      <Handle type="source" position={Position.Right} className="!bg-primary !w-2 !h-4 !rounded-sm !-right-[10px]" />
      <Handle type="source" position={Position.Bottom} className="!bg-primary !w-4 !h-2 !rounded-sm !-bottom-[10px]" />
    </div>
  );
});
