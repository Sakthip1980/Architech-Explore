import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Separator } from '@/components/ui/separator';
import { Play, Upload, Layers, Brain, Cpu, Plus, Trash2, Server, Network, Settings, Zap } from 'lucide-react';

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

const modelPresets = [
  { name: 'GPT-2 (124M)', id: 'gpt2', description: 'Transformer: 768 hidden, 12 layers' },
  { name: 'LLaMA 2 7B', id: 'llama2_7b', description: 'Llama: 4096 hidden, 32 layers' },
  { name: 'LLaMA 3.1 8B', id: 'llama3_8b', description: 'Llama: 4096 hidden, 32 layers, GQA' },
  { name: 'LLaMA 3.1 70B', id: 'llama3_70b', description: 'Llama: 8192 hidden, 80 layers, GQA' },
  { name: 'LLaMA 3.1 405B', id: 'llama3_405b', description: 'Llama: 16384 hidden, 126 layers' },
  { name: 'GPT-3 (175B)', id: 'gpt3_175b', description: 'GPT: 12288 hidden, 96 layers' },
  { name: 'BERT Base', id: 'bert_base', description: 'BERT: 768 hidden, 12 layers' },
  { name: 'BERT Large', id: 'bert_large', description: 'BERT: 1024 hidden, 24 layers' },
  { name: 'ResNet-50', id: 'resnet50', description: 'CNN: 50 layers, ImageNet' },
];

const hardwarePresets = [
  { name: 'NVIDIA A100 80GB', id: 'a100_80gb', tflops: 312, mem_bw: 1986 },
  { name: 'NVIDIA H100 SXM5', id: 'h100_sxm5_80gb', tflops: 989, mem_bw: 3440 },
  { name: 'NVIDIA V100 32GB', id: 'v100_32gb', tflops: 125, mem_bw: 900 },
  { name: 'Google TPU v3', id: 'tpu_v3', tflops: 123, mem_bw: 900 },
  { name: 'Custom', id: 'custom', tflops: 0, mem_bw: 0 },
];

const networkPresets = [
  { name: 'DGX V100 8 GPU', id: 'dgx_v100_8gpu', topology: 'Switch', gpus: 8, bw: 300 },
  { name: 'HGX H100 8 GPU', id: 'hgx_h100_8gpu', topology: 'Switch', gpus: 8, bw: 400 },
  { name: 'HGX H100 16 GPU', id: 'hgx_h100_16gpu', topology: 'Switch', gpus: 16, bw: 400 },
  { name: 'HGX H100 32 GPU', id: 'hgx_h100_32gpu', topology: 'Switch', gpus: 32, bw: 400 },
  { name: 'TPU v3 8', id: 'tpu_v3_8', topology: 'Ring', gpus: 8, bw: 656 },
  { name: 'TPU v3 32 Ring', id: 'tpu_v3_32_ring', topology: 'Ring', gpus: 32, bw: 656 },
  { name: 'TPU v3 32 Torus', id: 'tpu_v3_32_torus', topology: '2D Torus', gpus: 32, bw: 656 },
];

const precisionModes = [
  { name: 'FP32', id: 'fp32', bytes: 4 },
  { name: 'FP16', id: 'fp16', bytes: 2 },
  { name: 'BF16', id: 'bf16', bytes: 2 },
  { name: 'FP8', id: 'fp8', bytes: 1 },
  { name: 'INT8', id: 'int8', bytes: 1 },
  { name: 'Mixed FP16', id: 'mixed_fp16', bytes: 2 },
  { name: 'Mixed BF16', id: 'mixed_bf16', bytes: 2 },
];

export const WorkloadPanel = ({ onRunSimulation, isSimulating }: WorkloadPanelProps) => {
  const [selectedModel, setSelectedModel] = useState('gpt2');
  const [selectedHardware, setSelectedHardware] = useState('h100_sxm5_80gb');
  const [selectedNetwork, setSelectedNetwork] = useState('hgx_h100_8gpu');
  const [selectedPrecision, setSelectedPrecision] = useState('bf16');
  const [batchSize, setBatchSize] = useState(1);
  const [seqLen, setSeqLen] = useState(512);
  const [runType, setRunType] = useState<'training' | 'inference'>('inference');
  
  const [dpDegree, setDpDegree] = useState(1);
  const [tpDegree, setTpDegree] = useState(1);
  const [ppDegree, setPpDegree] = useState(1);
  const [cpDegree, setCpDegree] = useState(1);
  const [zeroStage, setZeroStage] = useState(0);
  const [numMicrobatches, setNumMicrobatches] = useState(1);
  
  const [useFlashAttention, setUseFlashAttention] = useState(true);
  
  const [customLayers, setCustomLayers] = useState<GEMMLayer[]>([
    { id: '1', name: 'layer_1', M: 1024, K: 1024, N: 1024 }
  ]);
  const [csvContent, setCsvContent] = useState('');

  const totalDevices = dpDegree * tpDegree * ppDegree * cpDegree;

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
    const workloadData: any = {
      type: 'llm',
      model_preset: selectedModel,
      hardware_preset: selectedHardware,
      network_preset: selectedNetwork,
      precision: selectedPrecision,
      batch: batchSize,
      seq_len: seqLen,
      run_type: runType,
      use_flashattention: useFlashAttention,
      parallelism: {
        dp: dpDegree,
        tp: tpDegree,
        pp: ppDegree,
        cp: cpDegree,
        dp_zero_stage: zeroStage,
        num_microbatches: numMicrobatches,
      }
    };
    
    if (customLayers.length > 0 && selectedModel === 'custom') {
      workloadData.type = 'custom';
      workloadData.layers = customLayers;
    }
    
    if (csvContent) {
      workloadData.type = 'csv';
      workloadData.content = csvContent;
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
          WORKLOAD & CONFIG
        </h2>
        <p className="text-[10px] text-muted-foreground mt-1">
          Configure hardware, model, and parallelism
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <Accordion type="multiple" defaultValue={['hardware', 'model']} className="space-y-2">
          <AccordionItem value="hardware" className="border border-sidebar-border rounded-lg">
            <AccordionTrigger className="px-3 py-2 hover:no-underline">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Server className="w-3 h-3 text-primary" />
                HARDWARE PRESET
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3 space-y-3">
              <Select value={selectedHardware} onValueChange={setSelectedHardware}>
                <SelectTrigger className="h-8 text-xs font-mono" data-testid="select-hardware">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {hardwarePresets.map(hw => (
                    <SelectItem key={hw.id} value={hw.id} className="text-xs font-mono">
                      {hw.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {selectedHardware !== 'custom' && (
                <div className="grid grid-cols-2 gap-2 text-[10px]">
                  <div className="bg-muted/50 p-2 rounded">
                    <span className="text-muted-foreground">Peak TFLOPS:</span>
                    <span className="ml-1 font-mono text-primary">
                      {hardwarePresets.find(h => h.id === selectedHardware)?.tflops}
                    </span>
                  </div>
                  <div className="bg-muted/50 p-2 rounded">
                    <span className="text-muted-foreground">Mem BW (GB/s):</span>
                    <span className="ml-1 font-mono text-primary">
                      {hardwarePresets.find(h => h.id === selectedHardware)?.mem_bw}
                    </span>
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Precision</Label>
                <Select value={selectedPrecision} onValueChange={setSelectedPrecision}>
                  <SelectTrigger className="h-7 text-xs font-mono" data-testid="select-precision">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {precisionModes.map(p => (
                      <SelectItem key={p.id} value={p.id} className="text-xs font-mono">
                        {p.name} ({p.bytes}B)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="model" className="border border-sidebar-border rounded-lg">
            <AccordionTrigger className="px-3 py-2 hover:no-underline">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Layers className="w-3 h-3 text-primary" />
                MODEL & WORKLOAD
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3 space-y-3">
              <Tabs defaultValue="preset" className="space-y-3">
                <TabsList className="grid w-full grid-cols-3 h-7">
                  <TabsTrigger value="preset" className="text-[10px] font-mono" data-testid="tab-preset">Preset</TabsTrigger>
                  <TabsTrigger value="custom" className="text-[10px] font-mono" data-testid="tab-custom">Custom</TabsTrigger>
                  <TabsTrigger value="csv" className="text-[10px] font-mono" data-testid="tab-csv">CSV</TabsTrigger>
                </TabsList>

                <TabsContent value="preset" className="space-y-3">
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger className="h-8 text-xs font-mono" data-testid="select-model">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {modelPresets.map(m => (
                        <SelectItem key={m.id} value={m.id} className="text-xs font-mono">
                          {m.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  <p className="text-[9px] text-muted-foreground">
                    {modelPresets.find(m => m.id === selectedModel)?.description}
                  </p>
                </TabsContent>

                <TabsContent value="custom" className="space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-mono text-muted-foreground uppercase">GEMM Layers</p>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-5 text-[9px] px-2"
                        onClick={addLayer}
                        data-testid="button-add-layer"
                      >
                        <Plus className="w-2 h-2 mr-1" /> Add
                      </Button>
                    </div>
                    
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {customLayers.map((layer, idx) => (
                        <Card key={layer.id} className="border-sidebar-border">
                          <CardContent className="p-2 space-y-1">
                            <div className="flex items-center justify-between">
                              <Input
                                value={layer.name}
                                onChange={(e) => updateLayer(layer.id, 'name', e.target.value)}
                                className="font-mono h-5 text-[10px] w-20"
                                data-testid={`input-layer-name-${idx}`}
                              />
                              <Button 
                                size="sm" 
                                variant="ghost" 
                                className="h-5 w-5 p-0"
                                onClick={() => removeLayer(layer.id)}
                                data-testid={`button-remove-layer-${idx}`}
                              >
                                <Trash2 className="w-2 h-2 text-destructive" />
                              </Button>
                            </div>
                            <div className="grid grid-cols-3 gap-1">
                              {(['M', 'K', 'N'] as const).map(dim => (
                                <div key={dim} className="space-y-0.5">
                                  <Label className="text-[8px] font-mono text-muted-foreground">{dim}</Label>
                                  <Input
                                    type="number"
                                    value={layer[dim]}
                                    onChange={(e) => updateLayer(layer.id, dim, e.target.value)}
                                    className="font-mono h-5 text-[10px]"
                                    data-testid={`input-layer-${dim.toLowerCase()}-${idx}`}
                                  />
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="csv" className="space-y-3">
                  <div className="border border-dashed border-sidebar-border rounded p-3 text-center">
                    <Upload className="w-6 h-6 mx-auto text-muted-foreground mb-1" />
                    <p className="text-[10px] text-muted-foreground mb-1">Upload CSV</p>
                    <input
                      type="file"
                      accept=".csv"
                      onChange={handleFileUpload}
                      className="hidden"
                      id="csv-upload"
                      data-testid="input-csv-upload"
                    />
                    <label htmlFor="csv-upload">
                      <Button size="sm" variant="outline" className="text-[10px] h-6" asChild>
                        <span>Choose File</span>
                      </Button>
                    </label>
                  </div>
                  <Textarea
                    value={csvContent}
                    onChange={(e) => setCsvContent(e.target.value)}
                    placeholder="Layer,M,K,N"
                    className="font-mono text-[10px] h-16 resize-none"
                    data-testid="textarea-csv"
                  />
                </TabsContent>
              </Tabs>

              <Separator />

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Batch Size</Label>
                  <Input
                    type="number"
                    value={batchSize}
                    onChange={(e) => setBatchSize(parseInt(e.target.value) || 1)}
                    className="font-mono h-7 text-xs"
                    data-testid="input-batch-size"
                  />
                </div>
                <div className="space-y-1">
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

              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Run Type</Label>
                <div className="flex gap-2">
                  <Button 
                    size="sm" 
                    variant={runType === 'training' ? 'default' : 'outline'}
                    className="flex-1 h-7 text-[10px]"
                    onClick={() => setRunType('training')}
                    data-testid="button-training"
                  >
                    Training
                  </Button>
                  <Button 
                    size="sm" 
                    variant={runType === 'inference' ? 'default' : 'outline'}
                    className="flex-1 h-7 text-[10px]"
                    onClick={() => setRunType('inference')}
                    data-testid="button-inference"
                  >
                    Inference
                  </Button>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-[10px] font-mono text-muted-foreground">FlashAttention</Label>
                <Switch 
                  checked={useFlashAttention} 
                  onCheckedChange={setUseFlashAttention}
                  data-testid="switch-flashattention"
                />
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="parallelism" className="border border-sidebar-border rounded-lg">
            <AccordionTrigger className="px-3 py-2 hover:no-underline">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Zap className="w-3 h-3 text-primary" />
                PARALLELISM
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3 space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Data Parallel (DP)</Label>
                  <Input
                    type="number"
                    value={dpDegree}
                    onChange={(e) => setDpDegree(Math.max(1, parseInt(e.target.value) || 1))}
                    className="font-mono h-7 text-xs"
                    data-testid="input-dp"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Tensor Parallel (TP)</Label>
                  <Input
                    type="number"
                    value={tpDegree}
                    onChange={(e) => setTpDegree(Math.max(1, parseInt(e.target.value) || 1))}
                    className="font-mono h-7 text-xs"
                    data-testid="input-tp"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Pipeline Parallel (PP)</Label>
                  <Input
                    type="number"
                    value={ppDegree}
                    onChange={(e) => setPpDegree(Math.max(1, parseInt(e.target.value) || 1))}
                    className="font-mono h-7 text-xs"
                    data-testid="input-pp"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Context Parallel (CP)</Label>
                  <Input
                    type="number"
                    value={cpDegree}
                    onChange={(e) => setCpDegree(Math.max(1, parseInt(e.target.value) || 1))}
                    className="font-mono h-7 text-xs"
                    data-testid="input-cp"
                  />
                </div>
              </div>

              <div className="bg-muted/50 p-2 rounded text-center">
                <span className="text-[10px] text-muted-foreground">Total Devices: </span>
                <span className="text-xs font-mono font-bold text-primary">{totalDevices}</span>
              </div>

              {dpDegree > 1 && (
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">ZeRO Stage</Label>
                  <Select value={String(zeroStage)} onValueChange={(v) => setZeroStage(parseInt(v))}>
                    <SelectTrigger className="h-7 text-xs font-mono" data-testid="select-zero">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0" className="text-xs font-mono">Stage 0 (DDP)</SelectItem>
                      <SelectItem value="1" className="text-xs font-mono">Stage 1 (Optimizer)</SelectItem>
                      <SelectItem value="2" className="text-xs font-mono">Stage 2 (+Gradients)</SelectItem>
                      <SelectItem value="3" className="text-xs font-mono">Stage 3 (+Parameters)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {ppDegree > 1 && (
                <div className="space-y-1">
                  <Label className="text-[10px] font-mono text-muted-foreground">Microbatches</Label>
                  <Input
                    type="number"
                    value={numMicrobatches}
                    onChange={(e) => setNumMicrobatches(Math.max(ppDegree, parseInt(e.target.value) || ppDegree))}
                    className="font-mono h-7 text-xs"
                    data-testid="input-microbatches"
                  />
                </div>
              )}
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="network" className="border border-sidebar-border rounded-lg">
            <AccordionTrigger className="px-3 py-2 hover:no-underline">
              <div className="flex items-center gap-2 text-xs font-mono">
                <Network className="w-3 h-3 text-primary" />
                NETWORK TOPOLOGY
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-3 pb-3 space-y-3">
              <Select value={selectedNetwork} onValueChange={setSelectedNetwork}>
                <SelectTrigger className="h-8 text-xs font-mono" data-testid="select-network">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {networkPresets.map(n => (
                    <SelectItem key={n.id} value={n.id} className="text-xs font-mono">
                      {n.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {selectedNetwork && (
                <div className="grid grid-cols-3 gap-2 text-[10px]">
                  <div className="bg-muted/50 p-2 rounded">
                    <span className="text-muted-foreground block">Topology</span>
                    <span className="font-mono text-primary">
                      {networkPresets.find(n => n.id === selectedNetwork)?.topology}
                    </span>
                  </div>
                  <div className="bg-muted/50 p-2 rounded">
                    <span className="text-muted-foreground block">GPUs</span>
                    <span className="font-mono text-primary">
                      {networkPresets.find(n => n.id === selectedNetwork)?.gpus}
                    </span>
                  </div>
                  <div className="bg-muted/50 p-2 rounded">
                    <span className="text-muted-foreground block">BW (Gb/s)</span>
                    <span className="font-mono text-primary">
                      {networkPresets.find(n => n.id === selectedNetwork)?.bw}
                    </span>
                  </div>
                </div>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
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
