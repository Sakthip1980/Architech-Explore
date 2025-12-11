import React, { useState } from 'react';
import { Sidebar } from '@/components/architecture/Sidebar';
import { FlowEditor } from '@/components/architecture/FlowEditor';
import { PropertiesPanel } from '@/components/architecture/PropertiesPanel';
import { useNodesState, useEdgesState, Node, Edge } from 'reactflow';
import { Toaster } from '@/components/ui/toaster';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Code } from 'lucide-react';

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

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showCode, setShowCode] = useState(false);

  const updateNodeData = (id: string, data: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === id) {
          // preserve position and other props, just update data
          return { ...node, data: { ...node.data, ...data } };
        }
        return node;
      })
    );
    // Also update selected node so the panel doesn't lose sync immediately
    if (selectedNode && selectedNode.id === id) {
      setSelectedNode((prev) => prev ? { ...prev, data: { ...prev.data, ...data } } : null);
    }
  };

  const deleteNode = (id: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== id));
    setEdges((eds) => eds.filter((edge) => edge.source !== id && edge.target !== id));
    setSelectedNode(null);
  };

  // Generate Python-like representation for display
  const generatePythonCode = () => {
    let code = "import arch_sim as sim\n\n# Initialize System\nsystem = sim.System(name='MyArchitecture')\n\n";
    
    nodes.forEach(node => {
      const type = node.data.label.replace(/\s+/g, '');
      code += `${type}_${node.id} = sim.${type}(\n`;
      code += `    bandwidth='${node.data.bandwidth}GB/s',\n`;
      code += `    latency='${node.data.latency}ns',\n`;
      code += `    freq='${node.data.frequency}GHz'\n`;
      code += `)\n`;
      code += `system.add_module(${type}_${node.id})\n\n`;
    });

    code += "# Connections\n";
    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);
      if (source && target) {
        const sourceType = source.data.label.replace(/\s+/g, '');
        const targetType = target.data.label.replace(/\s+/g, '');
        code += `system.connect(${sourceType}_${source.id}, ${targetType}_${target.id})\n`;
      }
    });

    code += "\n# Run Simulation\nresults = system.simulate(cycles=1000)";
    return code;
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <Sidebar />
      
      <main className="flex-1 relative flex flex-col h-full">
        <header className="h-12 border-b border-border bg-card/50 flex items-center justify-between px-4 z-10">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-muted-foreground">workspace / untitled_architecture.arch</span>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setShowCode(!showCode)}
              className="text-xs font-mono flex items-center gap-2 text-primary hover:text-primary/80 transition-colors"
            >
              <Code className="w-4 h-4" /> View Backend Model
            </button>
          </div>
        </header>

        <div className="flex-1 relative">
           <FlowEditor 
            onNodeSelect={setSelectedNode}
            onGraphUpdate={() => {}}
            nodes={nodes}
            edges={edges}
            setNodes={setNodes}
            setEdges={setEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
           />
           
           {/* Code Overlay Panel */}
           {showCode && (
             <div className="absolute bottom-0 left-0 right-0 h-1/3 bg-card border-t border-border shadow-2xl z-20 flex flex-col animate-in slide-in-from-bottom duration-300">
               <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/20">
                 <h3 className="font-mono text-xs font-bold text-primary">Generated Python Model</h3>
                 <button onClick={() => setShowCode(false)} className="text-muted-foreground hover:text-foreground">×</button>
               </div>
               <ScrollArea className="flex-1 p-4 bg-[#0d0d0d]">
                 <pre className="font-mono text-xs text-green-400/80 leading-relaxed">
                   {generatePythonCode()}
                 </pre>
               </ScrollArea>
             </div>
           )}
        </div>
      </main>

      <PropertiesPanel 
        selectedNode={selectedNode} 
        updateNodeData={updateNodeData}
        deleteNode={deleteNode}
      />
    </div>
  );
}
