import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Play, Upload, Layers, Brain, Cpu, Plus, Trash2 } from 'lucide-react';

interface GEMMLayer {
  id: string;
  name: string;
  M: number;
  K: number;
  N: number;
}

interface WorkloadPanelProps {
  onRunSimulation: (workload: any) => void;
  isSimulating: boolean;
}

const presetWorkloads = [
  { name: 'GPT-2 (124M)', id: 'gpt2', description: 'Transformer: 768 hidden, 12 layers' },
  { name: 'LLaMA-7B', id: 'llama7b', description: 'Transformer: 4096 hidden, 32 layers' },
  { name: 'ResNet-50', id: 'resnet50', description: 'CNN: 50 layers, ImageNet' },
  { name: 'Custom', id: 'custom', description: 'Define your own GEMM layers' },
];

export const WorkloadPanel = ({ onRunSimulation, isSimulating }: WorkloadPanelProps) => {
  const [selectedPreset, setSelectedPreset] = useState('gpt2');
  const [batchSize, setBatchSize] = useState(1);
  const [seqLen, setSeqLen] = useState(512);
  const [customLayers, setCustomLayers] = useState<GEMMLayer[]>([
    { id: '1', name: 'layer_1', M: 1024, K: 1024, N: 1024 }
  ]);
  const [csvContent, setCsvContent] = useState('');

  const addLayer = () => {
    const newId = String(customLayers.length + 1);
    setCustomLayers([...customLayers, {
      id: newId,
      name: `layer_${newId}`,
      M: 1024,
      K: 1024,
      N: 1024
    }]);
  };

  const removeLayer = (id: string) => {
    setCustomLayers(customLayers.filter(l => l.id !== id));
  };

  const updateLayer = (id: string, field: keyof GEMMLayer, value: any) => {
    setCustomLayers(customLayers.map(l => 
      l.id === id ? { ...l, [field]: field === 'name' ? value : parseInt(value) || 0 } : l
    ));
  };

  const handleRunSimulation = () => {
    let workloadData;
    
    if (selectedPreset === 'custom') {
      workloadData = {
        type: 'custom',
        layers: customLayers
      };
    } else if (csvContent) {
      workloadData = {
        type: 'csv',
        content: csvContent
      };
    } else {
      workloadData = {
        type: 'preset',
        preset: selectedPreset,
        batch: batchSize,
        seq_len: seqLen
      };
    }
    
    onRunSimulation(workloadData);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setCsvContent(event.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-sidebar-border">
        <h2 className="font-mono font-bold text-sm flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          WORKLOAD
        </h2>
        <p className="text-[10px] text-muted-foreground mt-1">
          Define DNN layers for simulation
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <Tabs defaultValue="preset" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3 h-8">
            <TabsTrigger value="preset" className="text-xs font-mono" data-testid="tab-preset">Preset</TabsTrigger>
            <TabsTrigger value="custom" className="text-xs font-mono" data-testid="tab-custom">Custom</TabsTrigger>
            <TabsTrigger value="csv" className="text-xs font-mono" data-testid="tab-csv">CSV</TabsTrigger>
          </TabsList>

          <TabsContent value="preset" className="space-y-4">
            <div className="grid gap-2">
              {presetWorkloads.filter(w => w.id !== 'custom').map((workload) => (
                <Card 
                  key={workload.id}
                  className={`cursor-pointer transition-all ${
                    selectedPreset === workload.id 
                      ? 'border-primary bg-primary/5' 
                      : 'border-sidebar-border hover:border-primary/50'
                  }`}
                  onClick={() => setSelectedPreset(workload.id)}
                  data-testid={`preset-${workload.id}`}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2">
                      <Layers className="w-4 h-4 text-primary" />
                      <div>
                        <p className="text-xs font-mono font-bold">{workload.name}</p>
                        <p className="text-[10px] text-muted-foreground">{workload.description}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Batch Size</Label>
                <Input
                  type="number"
                  value={batchSize}
                  onChange={(e) => setBatchSize(parseInt(e.target.value) || 1)}
                  className="font-mono h-7 text-xs"
                  data-testid="input-batch-size"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Sequence Length</Label>
                <Input
                  type="number"
                  value={seqLen}
                  onChange={(e) => setSeqLen(parseInt(e.target.value) || 512)}
                  className="font-mono h-7 text-xs"
                  data-testid="input-seq-len"
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="custom" className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-mono text-muted-foreground uppercase">GEMM Layers</p>
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="h-6 text-[10px]"
                  onClick={addLayer}
                  data-testid="button-add-layer"
                >
                  <Plus className="w-3 h-3 mr-1" /> Add
                </Button>
              </div>
              
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {customLayers.map((layer, idx) => (
                  <Card key={layer.id} className="border-sidebar-border">
                    <CardContent className="p-2 space-y-2">
                      <div className="flex items-center justify-between">
                        <Input
                          value={layer.name}
                          onChange={(e) => updateLayer(layer.id, 'name', e.target.value)}
                          className="font-mono h-6 text-xs w-24"
                          data-testid={`input-layer-name-${idx}`}
                        />
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          className="h-6 w-6 p-0"
                          onClick={() => removeLayer(layer.id)}
                          data-testid={`button-remove-layer-${idx}`}
                        >
                          <Trash2 className="w-3 h-3 text-destructive" />
                        </Button>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="space-y-0.5">
                          <Label className="text-[8px] font-mono text-muted-foreground">M</Label>
                          <Input
                            type="number"
                            value={layer.M}
                            onChange={(e) => updateLayer(layer.id, 'M', e.target.value)}
                            className="font-mono h-6 text-xs"
                            data-testid={`input-layer-m-${idx}`}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[8px] font-mono text-muted-foreground">K</Label>
                          <Input
                            type="number"
                            value={layer.K}
                            onChange={(e) => updateLayer(layer.id, 'K', e.target.value)}
                            className="font-mono h-6 text-xs"
                            data-testid={`input-layer-k-${idx}`}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[8px] font-mono text-muted-foreground">N</Label>
                          <Input
                            type="number"
                            value={layer.N}
                            onChange={(e) => updateLayer(layer.id, 'N', e.target.value)}
                            className="font-mono h-6 text-xs"
                            data-testid={`input-layer-n-${idx}`}
                          />
                        </div>
                      </div>
                      <p className="text-[8px] text-muted-foreground text-right">
                        {(2 * layer.M * layer.K * layer.N / 1e9).toFixed(2)} GOps
                      </p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="csv" className="space-y-4">
            <div className="space-y-3">
              <div className="border border-dashed border-sidebar-border rounded-lg p-4 text-center">
                <Upload className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                <p className="text-xs text-muted-foreground mb-2">Upload CSV topology file</p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="csv-upload"
                  data-testid="input-csv-upload"
                />
                <label htmlFor="csv-upload">
                  <Button size="sm" variant="outline" className="text-xs" asChild>
                    <span>Choose File</span>
                  </Button>
                </label>
              </div>

              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Or paste CSV content:</Label>
                <Textarea
                  value={csvContent}
                  onChange={(e) => setCsvContent(e.target.value)}
                  placeholder="Layer,M,K,N&#10;layer_1,1024,1024,1024"
                  className="font-mono text-xs h-24 resize-none"
                  data-testid="textarea-csv"
                />
              </div>

              <p className="text-[9px] text-muted-foreground">
                Format: Layer,M,K,N (GEMM) or Layer,N,C,H,W,K,R,S (Conv)
              </p>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <Button 
          className="w-full font-mono text-xs gap-2" 
          onClick={handleRunSimulation}
          disabled={isSimulating}
          data-testid="button-run-simulation"
        >
          {isSimulating ? (
            <>
              <Cpu className="w-3 h-3 animate-spin" /> Simulating...
            </>
          ) : (
            <>
              <Play className="w-3 h-3" /> Run Simulation
            </>
          )}
        </Button>
      </div>
    </div>
  );
};
