import React, { useState, useMemo } from 'react';
import { Sidebar } from '@/components/architecture/Sidebar';
import { FlowEditor } from '@/components/architecture/FlowEditor';
import { PropertiesPanel } from '@/components/architecture/PropertiesPanel';
import { WorkloadPanel } from '@/components/architecture/WorkloadPanel';
import { ResultsDashboard } from '@/components/architecture/ResultsDashboard';
import { KPILegend } from '@/components/architecture/KPIOverlay';
import { useNodesState, useEdgesState, Node, Edge } from 'reactflow';
import { Toaster } from '@/components/ui/toaster';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Code, Brain, Settings2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'custom',
    position: { x: 100, y: 100 },
    data: { label: 'Systolic Array', arrayHeight: '256', arrayWidth: '256', dataflow: 'OS', frequency: '1.0', power: '100' },
  },
  {
    id: '2',
    type: 'custom',
    position: { x: 400, y: 100 },
    data: { label: 'Scratchpad', sizeKb: '256', frequency: '1.0' },
  },
  {
    id: '3',
    type: 'custom',
    position: { x: 250, y: 280 },
    data: { label: 'HBM', generation: 'HBM2e', stacks: '4', bandwidth: '1024' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', type: 'dataflow', data: { bandwidth: 0, utilization: 0, isActive: false } },
  { id: 'e2-3', source: '2', target: '3', type: 'dataflow', data: { bandwidth: 0, utilization: 0, isActive: false } },
  { id: 'e1-3', source: '1', target: '3', type: 'dataflow', data: { bandwidth: 0, utilization: 0, isActive: false } },
];

export default function Home() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [rightPanelTab, setRightPanelTab] = useState<'properties' | 'workload'>('properties');
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResults, setSimulationResults] = useState<any>(null);
  const [showResults, setShowResults] = useState(false);
  const { toast } = useToast();

  React.useEffect(() => {
    if (!simulationResults?.summary) return;
    
    setNodes((nds) => nds.map(node => {
      let kpiUtilization: number | undefined;
      let kpiPower: number | undefined;
      let isBottleneck = false;
      
      if (node.data.label === 'Systolic Array') {
        kpiUtilization = simulationResults.summary.utilization_pct || 0;
        kpiPower = simulationResults.summary.power_watts || parseFloat(node.data.power) || 100;
        isBottleneck = (simulationResults.bottlenecks || []).some(
          (b: any) => b.component.includes('Systolic') && b.severity === 'high'
        );
      } else if (node.data.label === 'HBM' || node.data.label === 'DRAM Controller') {
        const memData = simulationResults.memory_hierarchy?.find(
          (m: any) => m.name.includes('HBM') || m.name.includes('DRAM')
        );
        kpiUtilization = memData?.bandwidth_util || 60;
        isBottleneck = (simulationResults.bottlenecks || []).some(
          (b: any) => b.component.includes('Memory') && b.severity === 'high'
        );
      } else if (node.data.label === 'Scratchpad' || node.data.label === 'SRAM Cache') {
        const memData = simulationResults.memory_hierarchy?.find(
          (m: any) => m.name.includes('Scratchpad') || m.name.includes('L1') || m.name.includes('L2')
        );
        kpiUtilization = memData?.bandwidth_util || 75;
      }
      
      return {
        ...node,
        data: {
          ...node.data,
          kpiUtilization,
          kpiPower,
          isBottleneck,
        }
      };
    }));
  }, [simulationResults, setNodes]);

  type EdgeData = { bandwidth: number; utilization: number; isActive: boolean };
  
  const edgeData = useMemo<Record<string, EdgeData>>(() => {
    if (!simulationResults?.summary) return {};
    
    const data: Record<string, EdgeData> = {};
    const utilization = simulationResults.summary.utilization_pct || 0;
    
    edges.forEach((edge, idx) => {
      const sourceNode = nodes.find(n => n.id === edge.source);
      const targetNode = nodes.find(n => n.id === edge.target);
      
      let bandwidth = 100;
      let edgeUtil = utilization * 0.8;
      
      if (sourceNode?.data.label === 'Systolic Array') {
        bandwidth = 512;
        edgeUtil = utilization;
      } else if (sourceNode?.data.label === 'HBM') {
        bandwidth = 1024;
        edgeUtil = utilization * 0.6;
      } else if (sourceNode?.data.label === 'Scratchpad') {
        bandwidth = 256;
        edgeUtil = utilization * 0.9;
      }
      
      data[edge.id] = {
        bandwidth,
        utilization: edgeUtil,
        isActive: true,
      };
    });
    
    return data;
  }, [simulationResults, edges, nodes]);

  const updateNodeData = (id: string, data: any) => {
    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === id) {
          return { ...node, data: { ...node.data, ...data } };
        }
        return node;
      })
    );
    if (selectedNode && selectedNode.id === id) {
      setSelectedNode((prev) => prev ? { ...prev, data: { ...prev.data, ...data } } : null);
    }
  };

  const deleteNode = (id: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== id));
    setEdges((eds) => eds.filter((edge) => edge.source !== id && edge.target !== id));
    setSelectedNode(null);
  };

  const handleRunWorkloadSimulation = async (workload: any) => {
    setIsSimulating(true);
    
    try {
      const res = await fetch('/api/simulator/workload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          graph: { nodes, edges },
          workload
        })
      });
      
      const data = await res.json();
      
      if (data.error) {
        toast({ 
          title: "Simulation Error", 
          description: data.error, 
          variant: "destructive" 
        });
      } else {
        setSimulationResults(data);
        setShowResults(true);
        toast({ 
          title: "Simulation Complete!", 
          description: `Utilization: ${data.summary?.utilization_pct?.toFixed(1)}% | Throughput: ${data.summary?.throughput_tflops?.toFixed(2)} TFLOPS`,
          duration: 5000,
        });
      }
    } catch (error: any) {
      toast({ 
        title: "Error", 
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsSimulating(false);
    }
  };

  const generatePythonCode = () => {
    let code = "import arch_sim as sim\nfrom arch_sim.models import DRAM, CPU, GPU, SystolicArray, Scratchpad, HBM\n\n# Initialize System\nsystem = sim.System(name='AI_Accelerator')\n\n";
    
    nodes.forEach(node => {
      const type = node.data.label.replace(/\s+/g, '');
      const varName = `${type}_${node.id}`.toLowerCase();
      
      if (node.data.label === 'Systolic Array') {
        code += `# Systolic Array for GEMM acceleration\n`;
        code += `${varName} = sim.SystolicArray(\n`;
        code += `    name='${node.data.label}',\n`;
        code += `    array_height=${node.data.arrayHeight || 256},\n`;
        code += `    array_width=${node.data.arrayWidth || 256},\n`;
        code += `    dataflow='${node.data.dataflow || 'OS'}',  # WS, OS, IS\n`;
        code += `    frequency_ghz=${node.data.frequency || 1.0},\n`;
        code += `    tdp_watts=${node.data.power || 100}\n`;
        code += `)\n`;
      } else if (node.data.label === 'HBM') {
        code += `# High Bandwidth Memory\n`;
        code += `${varName} = sim.HBM(\n`;
        code += `    generation='${node.data.generation || 'HBM2e'}',\n`;
        code += `    stacks=${node.data.stacks || 4},\n`;
        code += `    bandwidth_gbps=${node.data.bandwidth || 1024}\n`;
        code += `)\n`;
      } else if (node.data.label === 'Scratchpad') {
        code += `# On-chip Scratchpad Memory\n`;
        code += `${varName} = sim.Scratchpad(\n`;
        code += `    size_kb=${node.data.sizeKb || 256},\n`;
        code += `    frequency_ghz=${node.data.frequency || 1.0}\n`;
        code += `)\n`;
      } else {
        code += `${varName} = sim.${type}(\n`;
        code += `    bandwidth='${node.data.bandwidth}GB/s',\n`;
        code += `    latency='${node.data.latency}ns',\n`;
        code += `    freq='${node.data.frequency}GHz'\n`;
        code += `)\n`;
      }
      code += `system.add_module(${varName})\n\n`;
    });

    code += "# Connections\n";
    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source);
      const target = nodes.find(n => n.id === edge.target);
      if (source && target) {
        const sourceVar = `${source.data.label.replace(/\s+/g, '')}_${source.id}`.toLowerCase();
        const targetVar = `${target.data.label.replace(/\s+/g, '')}_${target.id}`.toLowerCase();
        code += `system.connect(${sourceVar}, ${targetVar})\n`;
      }
    });

    code += "\n# Run Workload Simulation\n";
    code += "workload = sim.Workload.gpt2(batch=1, seq_len=512)\n";
    code += "results = system.simulate_workload(workload)\n\n";
    code += "# Results\n";
    code += "print(f'Utilization: {results.utilization_pct:.1f}%')\n";
    code += "print(f'Throughput: {results.throughput_tflops:.2f} TFLOPS')";
    return code;
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden text-foreground">
      <Sidebar />
      
      <main className="flex-1 relative flex flex-col h-full">
        <header className="h-12 border-b border-border bg-card/50 flex items-center justify-between px-4 z-10">
          <div className="flex items-center gap-4">
            <span className="text-xs font-mono text-muted-foreground">workspace / ai_accelerator.arch</span>
            {simulationResults && (
              <button
                onClick={() => setShowResults(true)}
                className="text-[10px] font-mono bg-green-500/10 text-green-500 px-2 py-1 rounded flex items-center gap-1"
                data-testid="button-show-results"
              >
                View Results
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setShowCode(!showCode)}
              className="text-xs font-mono flex items-center gap-2 text-primary hover:text-primary/80 transition-colors"
              data-testid="button-view-code"
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
            edgeData={edgeData}
            simulationActive={!!simulationResults}
           />
           
           <KPILegend />
           
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

      <aside className="w-72 bg-sidebar border-l border-sidebar-border h-full flex flex-col z-10">
        <div className="border-b border-sidebar-border">
          <div className="flex">
            <button
              onClick={() => setRightPanelTab('properties')}
              className={`flex-1 p-3 text-xs font-mono flex items-center justify-center gap-2 transition-colors ${
                rightPanelTab === 'properties' 
                  ? 'bg-primary/10 text-primary border-b-2 border-primary' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              data-testid="tab-properties"
            >
              <Settings2 className="w-3 h-3" /> Properties
            </button>
            <button
              onClick={() => setRightPanelTab('workload')}
              className={`flex-1 p-3 text-xs font-mono flex items-center justify-center gap-2 transition-colors ${
                rightPanelTab === 'workload' 
                  ? 'bg-primary/10 text-primary border-b-2 border-primary' 
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              data-testid="tab-workload"
            >
              <Brain className="w-3 h-3" /> Workload
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-hidden">
          {rightPanelTab === 'properties' ? (
            <PropertiesPanel 
              selectedNode={selectedNode} 
              updateNodeData={updateNodeData}
              deleteNode={deleteNode}
            />
          ) : (
            <WorkloadPanel 
              onRunSimulation={handleRunWorkloadSimulation}
              isSimulating={isSimulating}
            />
          )}
        </div>
      </aside>

      <ResultsDashboard 
        results={simulationResults}
        isOpen={showResults}
        onClose={() => setShowResults(false)}
      />
      
      <Toaster />
    </div>
  );
}
