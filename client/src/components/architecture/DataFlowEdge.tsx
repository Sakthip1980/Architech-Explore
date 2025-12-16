import React from 'react';
import { EdgeProps, getBezierPath, EdgeLabelRenderer } from 'reactflow';

interface DataFlowData {
  bandwidth?: number;
  dataRate?: number;
  isActive?: boolean;
  utilization?: number;
}

export const DataFlowEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps<DataFlowData>) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const bandwidth = data?.bandwidth || 0;
  const utilization = data?.utilization || 0;
  const isActive = data?.isActive || false;

  const getStrokeColor = () => {
    if (!isActive) return 'rgb(100, 116, 139)';
    if (utilization >= 80) return 'rgb(34, 197, 94)';
    if (utilization >= 50) return 'rgb(234, 179, 8)';
    return 'rgb(239, 68, 68)';
  };

  const strokeWidth = isActive ? 2 + (utilization / 100) * 2 : 1.5;

  return (
    <>
      <defs>
        <linearGradient id={`gradient-${id}`} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={getStrokeColor()} stopOpacity="0.3" />
          <stop offset="50%" stopColor={getStrokeColor()} stopOpacity="1" />
          <stop offset="100%" stopColor={getStrokeColor()} stopOpacity="0.3" />
        </linearGradient>
        
        {isActive && (
          <filter id={`glow-${id}`}>
            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        )}
      </defs>

      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        stroke={getStrokeColor()}
        strokeWidth={strokeWidth}
        fill="none"
        style={{
          filter: isActive ? `url(#glow-${id})` : undefined,
        }}
      />

      {isActive && (
        <>
          <circle r="3" fill={getStrokeColor()}>
            <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
          </circle>
          <circle r="3" fill={getStrokeColor()}>
            <animateMotion dur="1.5s" repeatCount="indefinite" begin="0.5s" path={edgePath} />
          </circle>
          <circle r="3" fill={getStrokeColor()}>
            <animateMotion dur="1.5s" repeatCount="indefinite" begin="1s" path={edgePath} />
          </circle>
        </>
      )}

      {(bandwidth > 0 || utilization > 0) && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-none"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            }}
          >
            <div className={`
              px-1.5 py-0.5 rounded text-[8px] font-mono 
              ${isActive ? 'bg-card border border-sidebar-border shadow-md' : 'bg-card/50'}
            `}>
              {bandwidth > 0 && (
                <span className="text-primary">{bandwidth.toFixed(1)} GB/s</span>
              )}
              {bandwidth > 0 && utilization > 0 && <span className="text-muted-foreground mx-1">|</span>}
              {utilization > 0 && (
                <span className={
                  utilization >= 80 ? 'text-green-500' : 
                  utilization >= 50 ? 'text-yellow-500' : 'text-red-500'
                }>
                  {utilization.toFixed(0)}%
                </span>
              )}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
