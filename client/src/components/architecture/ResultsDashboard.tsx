import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { 
  BarChart3, Zap, Clock, Activity, AlertTriangle, 
  CheckCircle2, TrendingUp, Layers, Database 
} from 'lucide-react';

interface SimulationResults {
  summary?: {
    total_cycles: number;
    compute_cycles: number;
    stall_cycles: number;
    utilization_pct: number;
    throughput_tflops: number;
    total_energy_pj: number;
    power_watts: number;
  };
  per_layer?: Array<{
    name: string;
    cycles: number;
    utilization: number;
    stalls: number;
    bytes_moved: number;
  }>;
  memory_hierarchy?: Array<{
    name: string;
    bytes_accessed: number;
    energy_pj: number;
    bandwidth_util: number;
  }>;
  bottlenecks?: Array<{
    component: string;
    type: string;
    severity: 'low' | 'medium' | 'high';
    description: string;
  }>;
}

interface ResultsDashboardProps {
  results: SimulationResults | null;
  isOpen: boolean;
  onClose: () => void;
}

const MetricCard = ({ 
  icon: Icon, 
  label, 
  value, 
  unit, 
  color = 'text-primary',
  trend 
}: { 
  icon: any; 
  label: string; 
  value: string | number; 
  unit?: string;
  color?: string;
  trend?: 'up' | 'down' | 'neutral';
}) => (
  <Card className="border-sidebar-border bg-card/50">
    <CardContent className="p-3">
      <div className="flex items-start justify-between">
        <div className={`p-1.5 rounded ${color.replace('text-', 'bg-')}/10`}>
          <Icon className={`w-4 h-4 ${color}`} />
        </div>
        {trend && (
          <TrendingUp className={`w-3 h-3 ${
            trend === 'up' ? 'text-green-500' : 
            trend === 'down' ? 'text-red-500 rotate-180' : 
            'text-muted-foreground'
          }`} />
        )}
      </div>
      <p className="text-[10px] font-mono text-muted-foreground mt-2">{label}</p>
      <p className="text-lg font-mono font-bold">
        {value}
        {unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </p>
    </CardContent>
  </Card>
);

const UtilizationBar = ({ 
  label, 
  value, 
  color = 'bg-primary' 
}: { 
  label: string; 
  value: number; 
  color?: string;
}) => {
  const getColorClass = (v: number) => {
    if (v >= 80) return 'bg-green-500';
    if (v >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-mono">
        <span className="text-muted-foreground">{label}</span>
        <span className={value >= 80 ? 'text-green-500' : value >= 50 ? 'text-yellow-500' : 'text-red-500'}>
          {value.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div 
          className={`h-full ${getColorClass(value)} transition-all duration-500`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
    </div>
  );
};

const BottleneckItem = ({ bottleneck }: { bottleneck: any }) => {
  const severityColors = {
    low: 'border-yellow-500/30 bg-yellow-500/5 text-yellow-500',
    medium: 'border-orange-500/30 bg-orange-500/5 text-orange-500',
    high: 'border-red-500/30 bg-red-500/5 text-red-500'
  };

  const severityIcons = {
    low: CheckCircle2,
    medium: AlertTriangle,
    high: AlertTriangle
  };

  const Icon = severityIcons[bottleneck.severity as keyof typeof severityIcons];

  return (
    <div className={`p-3 rounded-lg border ${severityColors[bottleneck.severity as keyof typeof severityColors]}`}>
      <div className="flex items-start gap-2">
        <Icon className="w-4 h-4 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs font-mono font-bold">{bottleneck.component}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{bottleneck.description}</p>
        </div>
      </div>
    </div>
  );
};

export const ResultsDashboard = ({ results, isOpen, onClose }: ResultsDashboardProps) => {
  if (!isOpen || !results) return null;

  const summary = results.summary || {
    total_cycles: 0,
    compute_cycles: 0,
    stall_cycles: 0,
    utilization_pct: 0,
    throughput_tflops: 0,
    total_energy_pj: 0,
    power_watts: 0
  };

  const formatNumber = (n: number) => {
    if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return (n / 1e9).toFixed(2) + 'G';
    if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(2) + 'K';
    return n.toFixed(2);
  };

  return (
    <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="results-dashboard">
      <div className="bg-card border border-sidebar-border rounded-lg w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-4 border-b border-sidebar-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            <h2 className="font-mono font-bold">Simulation Results</h2>
          </div>
          <button 
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors text-xl"
            data-testid="button-close-results"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <Tabs defaultValue="summary" className="space-y-4">
            <TabsList className="grid w-full grid-cols-4 h-8">
              <TabsTrigger value="summary" className="text-xs font-mono" data-testid="tab-summary">Summary</TabsTrigger>
              <TabsTrigger value="layers" className="text-xs font-mono" data-testid="tab-layers">Per Layer</TabsTrigger>
              <TabsTrigger value="memory" className="text-xs font-mono" data-testid="tab-memory">Memory</TabsTrigger>
              <TabsTrigger value="bottlenecks" className="text-xs font-mono" data-testid="tab-bottlenecks">Bottlenecks</TabsTrigger>
            </TabsList>

            <TabsContent value="summary" className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <MetricCard 
                  icon={Clock} 
                  label="Total Cycles" 
                  value={formatNumber(summary.total_cycles)}
                  color="text-blue-500"
                />
                <MetricCard 
                  icon={Activity} 
                  label="Utilization" 
                  value={summary.utilization_pct.toFixed(1)}
                  unit="%"
                  color={summary.utilization_pct >= 80 ? 'text-green-500' : 'text-yellow-500'}
                />
                <MetricCard 
                  icon={Zap} 
                  label="Throughput" 
                  value={summary.throughput_tflops.toFixed(2)}
                  unit="TFLOPS"
                  color="text-purple-500"
                />
                <MetricCard 
                  icon={Zap} 
                  label="Power" 
                  value={summary.power_watts.toFixed(1)}
                  unit="W"
                  color="text-orange-500"
                />
              </div>

              <Card className="border-sidebar-border">
                <CardHeader className="p-3 pb-2">
                  <CardTitle className="text-xs font-mono">Cycle Breakdown</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-0 space-y-3">
                  <UtilizationBar 
                    label="Compute Cycles" 
                    value={(summary.compute_cycles / summary.total_cycles) * 100 || 0} 
                  />
                  <UtilizationBar 
                    label="Memory Stalls" 
                    value={(summary.stall_cycles / summary.total_cycles) * 100 || 0} 
                  />
                </CardContent>
              </Card>

              <Card className="border-sidebar-border">
                <CardHeader className="p-3 pb-2">
                  <CardTitle className="text-xs font-mono">Energy Breakdown</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">Total Energy</span>
                    <span className="text-sm font-mono font-bold">{formatNumber(summary.total_energy_pj)} pJ</span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-muted-foreground">Energy per Op</span>
                    <span className="text-sm font-mono font-bold">
                      {(summary.total_energy_pj / (summary.total_cycles * 1000) || 0).toFixed(2)} pJ/op
                    </span>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="layers" className="space-y-4">
              {results.per_layer && results.per_layer.length > 0 ? (
                <div className="space-y-2">
                  {results.per_layer.map((layer, idx) => (
                    <Card key={idx} className="border-sidebar-border">
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Layers className="w-4 h-4 text-primary" />
                            <span className="text-xs font-mono font-bold">{layer.name}</span>
                          </div>
                          <span className="text-[10px] text-muted-foreground">
                            {formatNumber(layer.cycles)} cycles
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <p className="text-[9px] text-muted-foreground">Utilization</p>
                            <p className={`text-sm font-mono font-bold ${
                              layer.utilization >= 80 ? 'text-green-500' : 
                              layer.utilization >= 50 ? 'text-yellow-500' : 'text-red-500'
                            }`}>
                              {layer.utilization.toFixed(1)}%
                            </p>
                          </div>
                          <div>
                            <p className="text-[9px] text-muted-foreground">Stalls</p>
                            <p className="text-sm font-mono font-bold">{formatNumber(layer.stalls)}</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-muted-foreground">Data Moved</p>
                            <p className="text-sm font-mono font-bold">{formatNumber(layer.bytes_moved)} B</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No per-layer data available</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="memory" className="space-y-4">
              {results.memory_hierarchy && results.memory_hierarchy.length > 0 ? (
                <div className="space-y-2">
                  {results.memory_hierarchy.map((mem, idx) => (
                    <Card key={idx} className="border-sidebar-border">
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Database className="w-4 h-4 text-violet-500" />
                            <span className="text-xs font-mono font-bold">{mem.name}</span>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div>
                            <p className="text-[9px] text-muted-foreground">Bytes Accessed</p>
                            <p className="text-sm font-mono font-bold">{formatNumber(mem.bytes_accessed)}</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-muted-foreground">Energy</p>
                            <p className="text-sm font-mono font-bold">{formatNumber(mem.energy_pj)} pJ</p>
                          </div>
                          <div>
                            <p className="text-[9px] text-muted-foreground">BW Util</p>
                            <p className={`text-sm font-mono font-bold ${
                              mem.bandwidth_util >= 80 ? 'text-green-500' : 
                              mem.bandwidth_util >= 50 ? 'text-yellow-500' : 'text-red-500'
                            }`}>
                              {mem.bandwidth_util.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No memory hierarchy data available</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="bottlenecks" className="space-y-4">
              {results.bottlenecks && results.bottlenecks.length > 0 ? (
                <div className="space-y-2">
                  {results.bottlenecks.map((bottleneck, idx) => (
                    <BottleneckItem key={idx} bottleneck={bottleneck} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-green-500/50">
                  <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
                  <p className="text-sm">No significant bottlenecks detected</p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};
