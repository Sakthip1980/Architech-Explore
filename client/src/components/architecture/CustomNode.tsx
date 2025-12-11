import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Cpu, Database, Network, HardDrive, Zap, CircuitBoard, GripHorizontal } from 'lucide-react';
import { clsx } from 'clsx';

const icons = {
  'CPU Core': Cpu,
  'GPU Accelerator': Zap,
  'DRAM Controller': Database,
  'NVM Storage': HardDrive,
  'NoC / Bus': Network,
  'Custom Logic': CircuitBoard,
};

const colors = {
  'CPU Core': 'border-cyan-500 shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)]',
  'GPU Accelerator': 'border-yellow-500 shadow-[0_0_15px_-3px_rgba(234,179,8,0.3)]',
  'DRAM Controller': 'border-purple-500 shadow-[0_0_15px_-3px_rgba(168,85,247,0.3)]',
  'NVM Storage': 'border-blue-500 shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)]',
  'NoC / Bus': 'border-green-500 shadow-[0_0_15px_-3px_rgba(34,197,94,0.3)]',
  'Custom Logic': 'border-pink-500 shadow-[0_0_15px_-3px_rgba(236,72,153,0.3)]',
};

const textColors = {
  'CPU Core': 'text-cyan-500',
  'GPU Accelerator': 'text-yellow-500',
  'DRAM Controller': 'text-purple-500',
  'NVM Storage': 'text-blue-500',
  'NoC / Bus': 'text-green-500',
  'Custom Logic': 'text-pink-500',
};

export const CustomNode = memo(({ data, selected }: NodeProps) => {
  const Icon = icons[data.label as keyof typeof icons] || CircuitBoard;
  const borderColor = colors[data.label as keyof typeof colors] || 'border-border';
  const textColor = textColors[data.label as keyof typeof textColors] || 'text-foreground';

  return (
    <div className={clsx(
      "px-4 py-3 min-w-[180px] rounded-md bg-card border-2 transition-all duration-200",
      selected ? borderColor : "border-border hover:border-border/80",
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
          <span className="font-mono text-[9px] text-muted-foreground uppercase tracking-wider">{data.frequency || '2.5'} GHz</span>
        </div>
      </div>

      <div className="space-y-1">
        <div className="flex justify-between text-[9px] font-mono text-muted-foreground">
          <span>BW:</span>
          <span className="text-foreground">{data.bandwidth || '128'} GB/s</span>
        </div>
        <div className="flex justify-between text-[9px] font-mono text-muted-foreground">
          <span>LAT:</span>
          <span className="text-foreground">{data.latency || '5'} ns</span>
        </div>
      </div>

      <div className="absolute -top-2 -right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <GripHorizontal className="w-4 h-4 text-muted-foreground/50" />
      </div>

      <Handle type="source" position={Position.Right} className="!bg-primary !w-2 !h-4 !rounded-sm !-right-[10px]" />
      <Handle type="source" position={Position.Bottom} className="!bg-primary !w-4 !h-2 !rounded-sm !-bottom-[10px]" />
    </div>
  );
});
