import React from 'react';
import { Node } from 'reactflow';
import { Activity, Zap, Clock, AlertTriangle } from 'lucide-react';

interface NodeKPIs {
  utilization?: number;
  power?: number;
  latency?: number;
  isBottleneck?: boolean;
  bottleneckType?: string;
}

interface KPIOverlayProps {
  node: Node;
  kpis: NodeKPIs;
  zoom: number;
}

export const KPIOverlay = ({ node, kpis, zoom }: KPIOverlayProps) => {
  if (!kpis || zoom < 0.5) return null;

  const { utilization, power, latency, isBottleneck, bottleneckType } = kpis;

  const getUtilizationColor = (u: number) => {
    if (u >= 80) return 'text-green-500 bg-green-500/10';
    if (u >= 50) return 'text-yellow-500 bg-yellow-500/10';
    return 'text-red-500 bg-red-500/10';
  };

  const scale = Math.max(0.6, Math.min(1, zoom));

  return (
    <div
      className="absolute pointer-events-none"
      style={{
        left: node.position.x + (node.width || 180) + 5,
        top: node.position.y,
        transform: `scale(${scale})`,
        transformOrigin: 'top left',
      }}
    >
      <div className="space-y-1">
        {utilization !== undefined && (
          <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono ${getUtilizationColor(utilization)}`}>
            <Activity className="w-2.5 h-2.5" />
            <span>{utilization.toFixed(1)}%</span>
          </div>
        )}
        
        {power !== undefined && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-orange-500 bg-orange-500/10">
            <Zap className="w-2.5 h-2.5" />
            <span>{power.toFixed(1)}W</span>
          </div>
        )}

        {latency !== undefined && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-blue-500 bg-blue-500/10">
            <Clock className="w-2.5 h-2.5" />
            <span>{latency.toFixed(1)}ns</span>
          </div>
        )}

        {isBottleneck && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono text-red-500 bg-red-500/10 animate-pulse">
            <AlertTriangle className="w-2.5 h-2.5" />
            <span>Bottleneck</span>
          </div>
        )}
      </div>
    </div>
  );
};

export const KPILegend = () => (
  <div className="absolute bottom-4 left-4 bg-card/90 border border-sidebar-border rounded-lg p-3 backdrop-blur-sm z-10">
    <p className="text-[10px] font-mono text-muted-foreground mb-2 uppercase">Component Status</p>
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-green-500" />
        <span className="text-[9px] font-mono">High utilization (80%+)</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-yellow-500" />
        <span className="text-[9px] font-mono">Medium utilization (50-80%)</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="w-3 h-3 rounded-full bg-red-500" />
        <span className="text-[9px] font-mono">Low utilization / Bottleneck</span>
      </div>
    </div>
  </div>
);
