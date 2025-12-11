import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Database, Network, HardDrive, Zap, CircuitBoard } from 'lucide-react';

export const Sidebar = () => {
  const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  const modules = [
    { type: 'cpu', label: 'CPU Core', icon: Cpu, color: 'text-cyan-400' },
    { type: 'gpu', label: 'GPU Accelerator', icon: Zap, color: 'text-yellow-400' },
    { type: 'memory', label: 'DRAM Controller', icon: Database, color: 'text-purple-400' },
    { type: 'storage', label: 'NVM Storage', icon: HardDrive, color: 'text-blue-400' },
    { type: 'interconnect', label: 'NoC / Bus', icon: Network, color: 'text-green-400' },
    { type: 'logic', label: 'Custom Logic', icon: CircuitBoard, color: 'text-pink-400' },
  ];

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border h-full flex flex-col p-4 z-10">
      <div className="mb-6">
        <h1 className="text-xl font-bold font-mono tracking-tight text-primary">ArchSim<span className="text-muted-foreground text-sm">.v1</span></h1>
        <p className="text-xs text-muted-foreground mt-1 font-mono">System Architecture Tool</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Library</h2>
        <div className="space-y-2">
          {modules.map((module) => (
            <div
              key={module.type}
              onDragStart={(event) => onDragStart(event, 'custom', module.label)}
              draggable
              className="group flex items-center gap-3 p-3 rounded-md border border-sidebar-border bg-card/50 hover:bg-sidebar-accent hover:border-primary/50 cursor-grab transition-all"
            >
              <module.icon className={`w-5 h-5 ${module.color}`} />
              <div className="flex flex-col">
                <span className="text-sm font-medium font-mono text-sidebar-foreground">{module.label}</span>
                <span className="text-[10px] text-muted-foreground">Module</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-sidebar-border">
        <div className="text-[10px] text-muted-foreground font-mono">
          <p>Drag components to canvas</p>
          <p className="mt-1 opacity-50">Python Backend: Disconnected</p>
        </div>
      </div>
    </aside>
  );
};
