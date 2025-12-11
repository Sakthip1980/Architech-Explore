import React, { useState, useCallback, useRef } from 'react';
import ReactFlow, {
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  BackgroundVariant,
  Connection,
  Edge,
  Node,
  Panel,
} from 'reactflow';
import { Button } from '@/components/ui/button';
import { Play, Download, Trash, RefreshCw } from 'lucide-react';
import { CustomNode } from './CustomNode';
import { useToast } from '@/hooks/use-toast';

const nodeTypes = {
  custom: CustomNode,
};

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'custom',
    position: { x: 250, y: 100 },
    data: { label: 'CPU Core', bandwidth: '64', latency: '2', frequency: '3.2', power: '45' },
  },
  {
    id: '2',
    type: 'custom',
    position: { x: 250, y: 300 },
    data: { label: 'DRAM Controller', bandwidth: '128', latency: '40', frequency: '1.2', power: '5' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } },
];

let id = 3;
const getId = () => `${id++}`;

interface FlowEditorProps {
  onNodeSelect: (node: Node | null) => void;
  onGraphUpdate: (nodes: Node[], edges: Edge[]) => void;
  nodes: Node[];
  edges: Edge[];
  setNodes: any;
  setEdges: any;
  onNodesChange: any;
  onEdgesChange: any;
}

const FlowEditorInner = ({ 
  onNodeSelect, 
  onGraphUpdate,
  nodes,
  edges,
  setNodes,
  setEdges,
  onNodesChange,
  onEdgesChange
}: FlowEditorProps) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  const { toast } = useToast();

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds: Edge[]) => addEdge({ ...params, animated: true, style: { stroke: '#06b6d4', strokeWidth: 2 } }, eds)),
    [setEdges],
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      const label = event.dataTransfer.getData('application/label');

      if (typeof type === 'undefined' || !type) {
        return;
      }

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: getId(),
        type: 'custom',
        position,
        data: { label: label, bandwidth: '100', latency: '10', frequency: '2.0', power: '20' },
      };

      setNodes((nds: Node[]) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes],
  );

  const onSelectionChange = useCallback(({ nodes }: { nodes: Node[] }) => {
    onNodeSelect(nodes[0] || null);
  }, [onNodeSelect]);

  // Update parent state whenever graph changes
  React.useEffect(() => {
    onGraphUpdate(nodes, edges);
  }, [nodes, edges, onGraphUpdate]);

  return (
    <div className="w-full h-full" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        className="bg-background"
        snapToGrid={true}
        snapGrid={[20, 20]}
      >
        <Controls className="!bg-card !border-border" />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#333" />
        
        <Panel position="top-right" className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            className="bg-card border-border hover:bg-muted font-mono text-xs gap-2"
            onClick={() => {
              setNodes(initialNodes);
              setEdges(initialEdges);
              toast({ title: "Reset", description: "Graph reset to default state" });
            }}
          >
            <RefreshCw className="w-3 h-3" /> Reset
          </Button>
          <Button 
            size="sm" 
            className="bg-primary hover:bg-primary/90 text-primary-foreground font-mono text-xs gap-2"
            onClick={() => {
              console.log({ nodes, edges });
              toast({ 
                title: "Simulating...", 
                description: "Exporting graph topology to Python backend (mocked).",
                duration: 3000,
              });
            }}
          >
            <Play className="w-3 h-3" /> Run Simulation
          </Button>
        </Panel>
      </ReactFlow>
    </div>
  );
};

export const FlowEditor = (props: any) => (
  <ReactFlowProvider>
    <FlowEditorInner {...props} />
  </ReactFlowProvider>
);
