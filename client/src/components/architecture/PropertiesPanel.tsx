import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Settings2, Trash2, Activity, Cpu, Database, Zap } from 'lucide-react';
import { Node } from 'reactflow';

interface PropertiesPanelProps {
  selectedNode: Node | null;
  updateNodeData: (id: string, data: any) => void;
  deleteNode: (id: string) => void;
}

const InputField = ({ label, name, register, placeholder, unit }: any) => (
  <div className="space-y-1.5">
    <Label className="text-[10px] font-mono text-muted-foreground">{label}</Label>
    <div className="relative">
      <Input 
        type="number" 
        step="any"
        placeholder={placeholder}
        {...register(name)} 
        className="font-mono bg-background/50 border-sidebar-border h-7 text-xs pr-8" 
      />
      {unit && <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[9px] text-muted-foreground">{unit}</span>}
    </div>
  </div>
);

export const PropertiesPanel = ({ selectedNode, updateNodeData, deleteNode }: PropertiesPanelProps) => {
  const { register, handleSubmit, reset, setValue, watch } = useForm();
  const label = selectedNode?.data?.label || '';

  useEffect(() => {
    if (selectedNode) {
      const d = selectedNode.data;
      reset({
        label: d.label,
        // Common
        bandwidth: d.bandwidth || '100',
        latency: d.latency || '10',
        frequency: d.frequency || '2.0',
        power: d.power || '20',
        // DRAM
        tCL: d.tCL || '16',
        tRCD: d.tRCD || '18',
        tRP: d.tRP || '18',
        tRAS: d.tRAS || '36',
        banks: d.banks || '16',
        busWidth: d.busWidth || '64',
        // HBM
        generation: d.generation || 'HBM2e',
        stacks: d.stacks || '4',
        capacityPerStack: d.capacityPerStack || '4',
        // Cache
        level: d.level || '2',
        sizeKb: d.sizeKb || '256',
        associativity: d.associativity || '8',
        // NVM
        technology: d.technology || '3DXPoint',
        capacityGb: d.capacityGb || '256',
        readLatency: d.readLatency || '300',
        writeLatency: d.writeLatency || '1000',
        // Scratchpad
        partitions: d.partitions || '4',
        // NPU
        macUnits: d.macUnits || '4096',
        precision: d.precision || 'INT8',
        sramMb: d.sramMb || '32',
        // DSP
        vectorWidth: d.vectorWidth || '256',
        // PCIe / CXL
        lanes: d.lanes || '16',
        // PCIe
        pcieGen: d.generation || '4',
        // CXL
        version: d.version || '2.0',
        cxlType: d.cxlType || '3',
        memoryGb: d.memoryGb || '128',
        // AXI
        axiVersion: d.version || 'AXI4',
        dataWidth: d.dataWidth || '128',
        frequencyMhz: d.frequencyMhz || '200',
        // DMA
        channels: d.channels || '8',
        // Memory Controller
        policy: d.policy || 'FR-FCFS',
        // CPU
        cores: d.cores || '4',
        // Systolic Array
        arrayHeight: d.arrayHeight || '256',
        arrayWidth: d.arrayWidth || '256',
        dataflow: d.dataflow || 'OS',
        precisionBytes: d.precisionBytes || '2',
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
      <div className="h-full p-4">
        <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-center p-6 border border-dashed border-sidebar-border rounded-lg bg-sidebar/50">
          <Settings2 className="w-10 h-10 mb-3 opacity-20" />
          <p className="text-sm font-mono">Select a module to configure parameters</p>
        </div>
      </div>
    );
  }

  const renderComponentSpecificFields = () => {
    switch (label) {
      case 'DRAM Controller':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-purple-400 font-mono flex items-center gap-2">
              <Database className="w-3 h-3" /> DRAM Timing
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="CAS Latency" name="tCL" register={register} placeholder="16" unit="cyc" />
              <InputField label="tRCD" name="tRCD" register={register} placeholder="18" unit="cyc" />
              <InputField label="tRP" name="tRP" register={register} placeholder="18" unit="cyc" />
              <InputField label="tRAS" name="tRAS" register={register} placeholder="36" unit="cyc" />
              <InputField label="Banks" name="banks" register={register} placeholder="16" />
              <InputField label="Bus Width" name="busWidth" register={register} placeholder="64" unit="bit" />
            </div>
          </div>
        );

      case 'HBM':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-violet-400 font-mono flex items-center gap-2">
              <Database className="w-3 h-3" /> HBM Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Generation</Label>
                <select {...register('generation')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="HBM2">HBM2</option>
                  <option value="HBM2e">HBM2e</option>
                  <option value="HBM3">HBM3</option>
                  <option value="HBM3e">HBM3e</option>
                </select>
              </div>
              <InputField label="Stacks" name="stacks" register={register} placeholder="4" />
              <InputField label="Cap/Stack" name="capacityPerStack" register={register} placeholder="4" unit="GB" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="2.4" unit="Gbps" />
            </div>
          </div>
        );

      case 'SRAM Cache':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-indigo-400 font-mono flex items-center gap-2">
              <Database className="w-3 h-3" /> Cache Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Level</Label>
                <select {...register('level')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="1">L1</option>
                  <option value="2">L2</option>
                  <option value="3">L3</option>
                </select>
              </div>
              <InputField label="Size" name="sizeKb" register={register} placeholder="256" unit="KB" />
              <InputField label="Associativity" name="associativity" register={register} placeholder="8" unit="way" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="3.0" unit="GHz" />
            </div>
          </div>
        );

      case 'NVM Storage':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-blue-400 font-mono flex items-center gap-2">
              <Database className="w-3 h-3" /> NVM Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Technology</Label>
                <select {...register('technology')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="3DXPoint">3D XPoint</option>
                  <option value="NAND">NAND</option>
                  <option value="ReRAM">ReRAM</option>
                </select>
              </div>
              <InputField label="Capacity" name="capacityGb" register={register} placeholder="256" unit="GB" />
              <InputField label="Read Lat" name="readLatency" register={register} placeholder="300" unit="ns" />
              <InputField label="Write Lat" name="writeLatency" register={register} placeholder="1000" unit="ns" />
            </div>
          </div>
        );

      case 'Scratchpad':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-sky-400 font-mono flex items-center gap-2">
              <Database className="w-3 h-3" /> Scratchpad Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Size" name="sizeKb" register={register} placeholder="256" unit="KB" />
              <InputField label="Partitions" name="partitions" register={register} placeholder="4" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="1.0" unit="GHz" />
            </div>
          </div>
        );

      case 'CPU Core':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-cyan-400 font-mono flex items-center gap-2">
              <Cpu className="w-3 h-3" /> CPU Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Cores" name="cores" register={register} placeholder="4" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="3.0" unit="GHz" />
              <InputField label="TDP" name="power" register={register} placeholder="65" unit="W" />
            </div>
          </div>
        );

      case 'GPU Accelerator':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-yellow-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> GPU Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Frequency" name="frequency" register={register} placeholder="1.5" unit="GHz" />
              <InputField label="Mem BW" name="bandwidth" register={register} placeholder="256" unit="GB/s" />
              <InputField label="TDP" name="power" register={register} placeholder="150" unit="W" />
            </div>
          </div>
        );

      case 'NPU':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-orange-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> NPU Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="MAC Units" name="macUnits" register={register} placeholder="4096" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="1.0" unit="GHz" />
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Precision</Label>
                <select {...register('precision')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="INT4">INT4</option>
                  <option value="INT8">INT8</option>
                  <option value="FP16">FP16</option>
                  <option value="BF16">BF16</option>
                  <option value="FP32">FP32</option>
                </select>
              </div>
              <InputField label="On-chip SRAM" name="sramMb" register={register} placeholder="32" unit="MB" />
              <InputField label="TDP" name="power" register={register} placeholder="30" unit="W" />
            </div>
          </div>
        );

      case 'DSP':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-amber-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> DSP Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Vector Width" name="vectorWidth" register={register} placeholder="256" unit="bit" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="1.2" unit="GHz" />
              <InputField label="TDP" name="power" register={register} placeholder="5" unit="W" />
            </div>
          </div>
        );

      case 'PCIe Link':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-teal-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> PCIe Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Generation</Label>
                <select {...register('generation')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="3">Gen 3</option>
                  <option value="4">Gen 4</option>
                  <option value="5">Gen 5</option>
                  <option value="6">Gen 6</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Lanes</Label>
                <select {...register('lanes')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="1">x1</option>
                  <option value="4">x4</option>
                  <option value="8">x8</option>
                  <option value="16">x16</option>
                </select>
              </div>
            </div>
          </div>
        );

      case 'CXL Interface':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-lime-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> CXL Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Version</Label>
                <select {...register('version')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="1.1">1.1</option>
                  <option value="2.0">2.0</option>
                  <option value="3.0">3.0</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Type</Label>
                <select {...register('cxlType')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="1">Type 1</option>
                  <option value="2">Type 2</option>
                  <option value="3">Type 3</option>
                </select>
              </div>
              <InputField label="Lanes" name="lanes" register={register} placeholder="16" />
              <InputField label="Memory" name="memoryGb" register={register} placeholder="128" unit="GB" />
            </div>
          </div>
        );

      case 'AXI Bus':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-emerald-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> AXI Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Version</Label>
                <select {...register('version')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="AXI3">AXI3</option>
                  <option value="AXI4">AXI4</option>
                  <option value="AXI4-Lite">AXI4-Lite</option>
                  <option value="AXI5">AXI5</option>
                </select>
              </div>
              <InputField label="Data Width" name="dataWidth" register={register} placeholder="128" unit="bit" />
              <InputField label="Frequency" name="frequencyMhz" register={register} placeholder="200" unit="MHz" />
            </div>
          </div>
        );

      case 'DMA Engine':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-pink-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> DMA Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Channels" name="channels" register={register} placeholder="8" />
              <InputField label="Bandwidth" name="bandwidth" register={register} placeholder="25.6" unit="GB/s" />
            </div>
          </div>
        );

      case 'Memory Controller':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-rose-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> MemCtrl Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Policy</Label>
                <select {...register('policy')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="FCFS">FCFS</option>
                  <option value="FR-FCFS">FR-FCFS</option>
                  <option value="BLISS">BLISS</option>
                  <option value="ATLAS">ATLAS</option>
                </select>
              </div>
              <InputField label="Channels" name="channels" register={register} placeholder="2" />
            </div>
          </div>
        );

      case 'Systolic Array':
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-red-400 font-mono flex items-center gap-2">
              <Zap className="w-3 h-3" /> Systolic Array Config
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Array Height" name="arrayHeight" register={register} placeholder="256" />
              <InputField label="Array Width" name="arrayWidth" register={register} placeholder="256" />
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Dataflow</Label>
                <select {...register('dataflow')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="OS">Output Stationary</option>
                  <option value="WS">Weight Stationary</option>
                  <option value="IS">Input Stationary</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-[10px] font-mono text-muted-foreground">Precision</Label>
                <select {...register('precisionBytes')} className="w-full h-7 text-xs font-mono bg-background/50 border border-sidebar-border rounded px-2">
                  <option value="1">INT8 (1B)</option>
                  <option value="2">FP16 (2B)</option>
                  <option value="4">FP32 (4B)</option>
                </select>
              </div>
              <InputField label="Frequency" name="frequency" register={register} placeholder="1.0" unit="GHz" />
              <InputField label="TDP" name="power" register={register} placeholder="100" unit="W" />
            </div>
          </div>
        );

      default:
        return (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-primary font-mono flex items-center gap-2">
              <Activity className="w-3 h-3" /> Performance
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <InputField label="Bandwidth" name="bandwidth" register={register} placeholder="100" unit="GB/s" />
              <InputField label="Latency" name="latency" register={register} placeholder="10" unit="ns" />
              <InputField label="Frequency" name="frequency" register={register} placeholder="2.0" unit="GHz" />
              <InputField label="Power" name="power" register={register} placeholder="20" unit="W" />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="h-full flex flex-col">
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
              <Label className="text-xs font-mono text-muted-foreground uppercase">Module Type</Label>
              <div className="font-mono bg-background/50 border border-sidebar-border rounded px-3 py-2 text-sm text-foreground">
                {label}
              </div>
            </div>
            
            <Separator className="bg-sidebar-border" />

            {renderComponentSpecificFields()}
          </div>
        </form>
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <Button 
          variant="destructive" 
          size="sm" 
          className="w-full font-mono text-xs gap-2"
          onClick={() => deleteNode(selectedNode.id)}
          data-testid="button-delete-node"
        >
          <Trash2 className="w-3 h-3" /> Remove Module
        </Button>
      </div>
    </div>
  );
};
