import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Settings2, Trash2, Activity } from 'lucide-react';
import { Node } from 'reactflow';

interface PropertiesPanelProps {
  selectedNode: Node | null;
  updateNodeData: (id: string, data: any) => void;
  deleteNode: (id: string) => void;
}

export const PropertiesPanel = ({ selectedNode, updateNodeData, deleteNode }: PropertiesPanelProps) => {
  const { register, handleSubmit, reset, setValue } = useForm();

  useEffect(() => {
    if (selectedNode) {
      reset({
        label: selectedNode.data.label,
        bandwidth: selectedNode.data.bandwidth || '128',
        latency: selectedNode.data.latency || '5',
        frequency: selectedNode.data.frequency || '2.5',
        power: selectedNode.data.power || '15',
      });
    }
  }, [selectedNode, reset]);

  const onSubmit = (data: any) => {
    if (selectedNode) {
      updateNodeData(selectedNode.id, data);
    }
  };

  if (!selectedNode) {
    return (
      <aside className="w-72 bg-sidebar border-l border-sidebar-border h-full p-4 z-10 hidden md:block">
        <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-center p-6 border border-dashed border-sidebar-border rounded-lg bg-sidebar/50">
          <Settings2 className="w-10 h-10 mb-3 opacity-20" />
          <p className="text-sm font-mono">Select a module to configure parameters</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-72 bg-sidebar border-l border-sidebar-border h-full flex flex-col z-10">
      <div className="p-4 border-b border-sidebar-border flex items-center justify-between">
        <h2 className="font-mono font-bold text-sm flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-primary" />
          PROPERTIES
        </h2>
        <span className="text-[10px] font-mono bg-primary/10 text-primary px-2 py-0.5 rounded">
          ID: {selectedNode.id.slice(0, 4)}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <form onChange={handleSubmit(onSubmit)} className="space-y-6">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label className="text-xs font-mono text-muted-foreground uppercase">Module Name</Label>
              <Input {...register('label')} className="font-mono bg-background/50 border-sidebar-border h-8 text-sm" />
            </div>
            
            <Separator className="bg-sidebar-border" />

            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-primary font-mono flex items-center gap-2">
                <Activity className="w-3 h-3" /> Performance
              </h3>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[10px] font-mono text-muted-foreground">Bandwidth (GB/s)</Label>
                  <Input 
                    type="number" 
                    {...register('bandwidth')} 
                    className="font-mono bg-background/50 border-sidebar-border h-7 text-xs" 
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[10px] font-mono text-muted-foreground">Latency (ns)</Label>
                  <Input 
                    type="number" 
                    {...register('latency')} 
                    className="font-mono bg-background/50 border-sidebar-border h-7 text-xs" 
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[10px] font-mono text-muted-foreground">Clock (GHz)</Label>
                  <Input 
                    type="number" 
                    {...register('frequency')} 
                    className="font-mono bg-background/50 border-sidebar-border h-7 text-xs" 
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[10px] font-mono text-muted-foreground">TDP (Watts)</Label>
                  <Input 
                    type="number" 
                    {...register('power')} 
                    className="font-mono bg-background/50 border-sidebar-border h-7 text-xs" 
                  />
                </div>
              </div>
            </div>
          </div>
        </form>

        <div className="mt-8 p-3 bg-primary/5 rounded border border-primary/10">
          <h4 className="text-[10px] font-mono text-primary mb-2 font-bold">SIMULATION PREVIEW</h4>
          <div className="space-y-1 text-[10px] font-mono text-muted-foreground">
            <div className="flex justify-between">
              <span>Throughput:</span>
              <span className="text-foreground">~{(parseFloat(selectedNode.data.bandwidth || 0) * 0.85).toFixed(1)} GB/s</span>
            </div>
            <div className="flex justify-between">
              <span>Idle Power:</span>
              <span className="text-foreground">{(parseFloat(selectedNode.data.power || 0) * 0.15).toFixed(1)} W</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <Button 
          variant="destructive" 
          size="sm" 
          className="w-full font-mono text-xs gap-2"
          onClick={() => deleteNode(selectedNode.id)}
        >
          <Trash2 className="w-3 h-3" /> Remove Module
        </Button>
      </div>
    </aside>
  );
};
