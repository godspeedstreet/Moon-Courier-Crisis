import { useEffect, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { X, CheckCircle, AlertTriangle, Zap, Clock, MapPin, Truck, Package, AlertCircle, Info, Coins, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Card, CardContent } from '../ui/Card';
import { Progress } from '../ui/Progress';
import type { Order, Rover } from '../../types';
import { getHexCorners } from '../../lib/hex';
import { deliveryApi, roversApi, ordersApi, gameApi } from '../../lib/api';
import { useGameStore } from '../../store/gameStore';
import { toast } from '../../hooks/use-toast';

interface SimulationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  order: Order | null;
  rovers: Rover[];
  onConfirm: (roverId: number) => void;
}

export function SimulationModal({ open, onOpenChange, order, rovers, onConfirm }: SimulationModalProps) {
  const [selectedRoverId, setSelectedRoverId] = useState<number | null>(null);
  const [simulation, setSimulation] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const { setRovers, setOrders, setGameState } = useGameStore();

  useEffect(() => {
    if (!selectedRoverId || !order) return;
    
    const runSimulation = async () => {
      setLoading(true);
      try {
        const data = await deliveryApi.simulate(selectedRoverId, order.id);
        setSimulation(data);
      } catch (e) {
        console.error('Simulation failed:', e);
      } finally {
        setLoading(false);
      }
    };
    
    runSimulation();
  }, [selectedRoverId, order]);

  const handleConfirm = async () => {
    if (!selectedRoverId || !order) return;
    setConfirmLoading(true);
    try {
      await deliveryApi.assign(selectedRoverId, order.id);

      const [updatedRovers, updatedOrders, updatedState] = await Promise.all([
        roversApi.getAll(),
        ordersApi.getAll(),
        gameApi.getState(),
      ]);

      setRovers(updatedRovers);
      setOrders(updatedOrders);
      setGameState(updatedState);

      toast({
        title: 'Ровер отправлен',
        description: `${selectedRover?.name ?? 'Ровер'} в пути — результат станет известен в конце дня`,
      });
      onConfirm(selectedRoverId);
      onOpenChange(false);
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка отправки ровера');
    } finally {
      setConfirmLoading(false);
    }
  };

  useEffect(() => {
    if (!open) {
      setSelectedRoverId(null);
      setSimulation(null);
    }
  }, [open]);

  const availableRovers = rovers.filter(r => r.status === 'idle' && r.max_cargo >= (order?.weight || 0));
  const selectedRover = rovers.find(r => r.id === selectedRoverId);
  const isFeasible = simulation?.success ?? false;
  const successChance = simulation?.success_chance ?? (1 - (simulation?.risk_score ?? 0));
  const isRisky = isFeasible && successChance < 0.7;

  if (!order) return null;

  return (
    <AnimatePresence>
      {open && (
        <Dialog open={open} onOpenChange={onOpenChange}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
            <DialogHeader className="border-b border-moon-700">
              <DialogTitle className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-500/20 rounded-lg">
                    <Package className="w-6 h-6 text-yellow-400" />
                  </div>
                  <div>
                    <div className="font-semibold">{order.title}</div>
                    <div className="text-sm text-moon-400">{order.description}</div>
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}>
                  <X className="w-5 h-5" />
                </Button>
              </DialogTitle>
              <DialogDescription>
                Выберите ровер и проверьте параметры доставки перед отправкой
              </DialogDescription>
            </DialogHeader>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 overflow-y-auto max-h-[calc(90vh-200px)]">
              <div className="space-y-4">
                <Card>
                  <CardContent className="pt-0">
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <Truck className="w-4 h-4" />
                      Доступные роверы ({availableRovers.length})
                    </h4>
                    {availableRovers.length === 0 ? (
                      <div className="text-center py-6 text-moon-500">
                        <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>Нет подходящих роверов</p>
                        <p className="text-xs mt-1">Требуется: грузоподъёмность ≥ {order.weight} кг, статус «В ожидании»</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {availableRovers.map(rover => (
                          <RoverOption 
                            key={rover.id} 
                            rover={rover} 
                            selected={selectedRoverId === rover.id}
                            onClick={() => setSelectedRoverId(rover.id)}
                          />
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="pt-0 space-y-3">
                    <h4 className="font-medium flex items-center gap-2">
                      <MapPin className="w-4 h-4" />
                      Детали заказа
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <StatItem label="Вес" value={`${order.weight.toFixed(1)} кг`} icon={<Package className="w-4 h-4" />} />
                      <StatItem label="Награда" value={`${order.reward.toFixed(0)} ₡`} icon={<Coins className="w-4 h-4 text-yellow-400" />} />
                      <StatItem label="Срочность" value={<UrgencyStars urgency={order.urgency} />} icon={<Clock className="w-4 h-4 text-yellow-400" />} />
                      <StatItem label="Риск" value={<RiskStars risk={order.risk_level} />} icon={<AlertTriangle className="w-4 h-4 text-red-400" />} />
                      <StatItem label="Забор" value={`(${order.pickup_q}, ${order.pickup_r})`} icon={<MapPin className="w-4 h-4 text-green-400" />} />
                      <StatItem label="Доставка" value={`(${order.delivery_q}, ${order.delivery_r})`} icon={<MapPin className="w-4 h-4 text-blue-400" />} />
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-4">
                {selectedRover && simulation && (
                  <>
                    <Card>
                      <CardContent className="pt-0 space-y-4">
                        <h4 className="font-medium flex items-center gap-2">
                          <Zap className="w-4 h-4" />
                          Результат симуляции
                        </h4>
                        
                        <div className={'p-3 rounded-lg text-center ' + (isFeasible ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30')}>
                          <div className="flex items-center justify-center gap-2 mb-2">
                            {isFeasible ? (
                              <CheckCircle className="w-6 h-6 text-green-400" />
                            ) : (
                              <AlertTriangle className="w-6 h-6 text-red-400" />
                            )}
                            <span className="text-lg font-semibold" style={{ color: isFeasible ? '#22c55e' : '#ef4444' }}>
                              {isFeasible ? 'Доставка возможна' : 'Доставка невозможна'}
                            </span>
                          </div>
                          {!isFeasible && simulation.failure_reason && (
                            <p className="text-sm text-moon-400">{simulation.failure_reason}</p>
                          )}
                          {isFeasible && isRisky && (
                            <p className="text-sm text-yellow-400">Высокий риск провала — отправляйте с осторожностью</p>
                          )}
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <SimStat label="Расстояние" value={`${simulation.distance.toFixed(1)} км`} />
                          <SimStat label="Время" value={`${simulation.time_estimate.toFixed(1)} ч`} />
                          <SimStat label="Батарея" value={`${simulation.battery_needed.toFixed(1)}%`} />
                          <SimStat label="Риск провала" value={`${(simulation.risk_score * 100).toFixed(0)}%`} />
                          <SimStat label="Награда" value={`${order.reward.toFixed(0)} ₡`} highlight />
                          <SimStat label="Шанс успеха" value={`${(successChance * 100).toFixed(0)}%`} />
                        </div>

                        <div className="pt-2 border-t border-moon-700">
                          <div className="flex justify-between text-sm mb-1">
                            <span>Батарея ровера после доставки</span>
                            <span className="font-mono">
                              {selectedRover.current_battery - simulation.battery_needed >= 0 ? 
                                `${(selectedRover.current_battery - simulation.battery_needed).toFixed(1)}%` : 
                                `<span className="text-red-400">Не хватит!</span>`
                              }
                            </span>
                          </div>
                          <Progress 
                            value={Math.max(0, selectedRover.current_battery - simulation.battery_needed)} 
                            max={selectedRover.max_battery} 
                            variant={selectedRover.current_battery - simulation.battery_needed > 20 ? 'success' : 'warning'} 
                            className="h-2"
                          />
                        </div>

                        {simulation.warnings && simulation.warnings.length > 0 && (
                          <div className="pt-2 border-t border-moon-700">
                            <h5 className="text-sm font-medium text-yellow-400 flex items-center gap-1 mb-2">
                              <AlertTriangle className="w-4 h-4" />
                              Предупреждения
                            </h5>
                            <ul className="space-y-1 text-sm text-moon-400">
                              {simulation.warnings.map((w: string, i: number) => (
                                <li key={i} className="flex items-start gap-2">
                                  <Info className="w-3 h-3 mt-0.5 flex-shrink-0 text-yellow-400" />
                                  {w}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="pt-0">
                        <h4 className="font-medium mb-3 flex items-center gap-2">
                          <MapPin className="w-4 h-4" />
                          Маршрут
                        </h4>
                        <MiniMapPreview 
                          path={simulation.path} 
                          order={order}
                          rover={selectedRover}
                        />
                      </CardContent>
                    </Card>
                  </>
                )}

                {!selectedRover && (
                  <Card>
                    <CardContent className="pt-0 py-8 text-center text-moon-500">
                      <Info className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p>Выберите ровер для симуляции</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>

            <DialogFooter className="border-t border-moon-700">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={confirmLoading}>
                Отмена
              </Button>
              <Button 
                variant={isRisky ? 'destructive' : 'default'} 
                onClick={handleConfirm}
                disabled={!selectedRoverId || loading || confirmLoading || !isFeasible}
                className="ml-auto"
              >
                {confirmLoading ? <> <Loader2 className="w-4 h-4 animate-spin mr-2" /> Отправка... </> : loading ? 'Расчёт...' : isRisky ? 'Отправить (рискованно)' : 'Отправить ровер'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </AnimatePresence>
  );
}

function RoverOption({ rover, selected, onClick }: { rover: Rover; selected: boolean; onClick: () => void }) {
  const batteryPct = rover.current_battery / rover.max_battery * 100;
  const batteryColor = batteryPct > 50 ? 'success' : batteryPct > 20 ? 'warning' : 'destructive';
  
  return (
    <button
      onClick={onClick}
      className={'w-full p-3 rounded-lg border transition-all text-left ' + 
        (selected 
          ? 'border-moon-400 bg-moon-800/50 shadow-lg shadow-moon-400/10' 
          : 'border-moon-700 hover:border-moon-600 hover:bg-moon-800/30')
      }
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg">
            <Truck className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <div className="font-medium">{rover.name}</div>
            <div className="text-xs text-moon-400">
              Батарея: {Math.round(rover.current_battery)}% • Груз: {rover.max_cargo} кг
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Progress value={rover.current_battery} max={rover.max_battery} variant={batteryColor} className="w-24 h-1.5" />
          {selected && <CheckCircle className="w-5 h-5 text-moon-400" />}
        </div>
      </div>
    </button>
  );
}

function StatItem({ label, value, icon }: { label: string; value: React.ReactNode; icon: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 p-2 bg-moon-800/50 rounded">
      <span className="text-moon-500">{icon}</span>
      <div>
        <div className="text-xs text-moon-500">{label}</div>
        <div className="font-mono text-sm">{value}</div>
      </div>
    </div>
  );
}

function SimStat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={'p-3 rounded-lg bg-moon-800/50 ' + (highlight ? 'bg-yellow-500/10 border border-yellow-500/20' : '')}>
      <div className="text-xs text-moon-500">{label}</div>
      <div className={'font-mono text-lg ' + (highlight ? 'text-yellow-300' : '')}>{value}</div>
    </div>
  );
}

function UrgencyStars({ urgency }: { urgency: number }) {
  return (
    <span className="text-yellow-400 font-mono">
      {'★'.repeat(urgency)}{'☆'.repeat(5 - urgency)}
    </span>
  );
}

function RiskStars({ risk }: { risk: number }) {
  return (
    <span className="text-red-400 font-mono">
      {'⚠'.repeat(risk)}
    </span>
  );
}

function MiniMapPreview({ path, order, rover }: { path: Array<{q: number, r: number}>; order: Order; rover: Rover }) {
  if (!path || path.length < 2) return <div className="text-center py-8 text-moon-500">Нет пути</div>;

  const allPoints = [
    { q: rover.base_q, r: rover.base_r },
    { q: order.pickup_q, r: order.pickup_r },
    { q: order.delivery_q, r: order.delivery_r },
    ...path
  ];
  
  const minQ = Math.min(...allPoints.map(p => p.q));
  const maxQ = Math.max(...allPoints.map(p => p.q));
  const minR = Math.min(...allPoints.map(p => p.r));
  const maxR = Math.max(...allPoints.map(p => p.r));

  const width = 300;
  const height = 200;
  const padding = 20;
  
  const qRange = maxQ - minQ || 1;
  const rRange = maxR - minR || 1;
  const scale = Math.min(
    (width - 2 * padding) / (qRange * 1.5),
    (height - 2 * padding) / (rRange * 1.732)
  );

  const centerX = width / 2;
  const centerY = height / 2;
  const offsetQ = (minQ + maxQ) / 2;
  const offsetR = (minR + maxR) / 2;

  const project = (q: number, r: number) => {
    const x = centerX + (q - offsetQ) * scale * 1.5;
    const y = centerY + (r - offsetR + (q - offsetQ) * 0.5) * scale * 1.732;
    return { x, y };
  };

  const pathPoints = path.map(p => project(p.q, p.r));
  const pathStr = pathPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  const basePos = project(rover.base_q, rover.base_r);
  const pickupPos = project(order.pickup_q, order.pickup_r);
  const deliveryPos = project(order.delivery_q, order.delivery_r);

  return (
    <svg width={width} height={height} className="rounded bg-moon-900/50" viewBox="0 0 300 200">
      <g stroke="#1e293b" strokeWidth="0.5" opacity="0.5">
        {path.map(p => {
          const pos = project(p.q, p.r);
          const corners = getHexCorners(pos.x, pos.y, 12);
          return <polygon key={`${p.q}-${p.r}`} points={corners} fill="none" />;
        })}
      </g>

      <path 
        d={pathStr} 
        stroke="#3b82f6" 
        strokeWidth={3} 
        fill="none" 
        strokeLinecap="round" 
        strokeLinejoin="round"
        strokeDasharray="8,4"
        className="animate-draw"
      />

      <g>
        <circle cx={basePos.x} cy={basePos.y} r={10} fill="#1e3a5f" stroke="#3b82f6" strokeWidth={2} />
        <text x={basePos.x} y={basePos.y + 20} textAnchor="middle" fill="#3b82f6" fontSize="9" fontFamily="monospace">БАЗА</text>
      </g>

      <g>
        <circle cx={pickupPos.x} cy={pickupPos.y} r={8} fill="#1e293b" stroke="#fbbf24" strokeWidth={2} />
        <text x={pickupPos.x} y={pickupPos.y - 12} textAnchor="middle" fill="#fbbf24" fontSize="8" fontFamily="monospace">📦</text>
      </g>

      <g>
        <circle cx={deliveryPos.x} cy={deliveryPos.y} r={8} fill="#1e293b" stroke="#22c55e" strokeWidth={2} strokeDasharray="3,2" />
        <text x={deliveryPos.x} y={deliveryPos.y - 12} textAnchor="middle" fill="#22c55e" fontSize="8" fontFamily="monospace">🎯</text>
      </g>

      <circle cx={basePos.x} cy={basePos.y} r={6} fill="#3b82f6" />
    </svg>
  );
}

const style = document.createElement('style');
style.textContent = `
  @keyframes draw {
    from { stroke-dashoffset: 1000; }
    to { stroke-dashoffset: 0; }
  }
  .animate-draw {
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
    animation: draw 1.5s ease-out forwards;
  }
`;
if (typeof document !== 'undefined') document.head.appendChild(style);