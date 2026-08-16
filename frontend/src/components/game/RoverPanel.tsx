import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import type { Rover, RoverStatus, RoverCreate } from '../../types';
import { useGameStore } from '../../store/gameStore';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Progress } from '../ui/Progress';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/Dialog';
import { roversApi } from '../../lib/api';
import { Truck, Package, Zap, RotateCcw, AlertTriangle, Plus, Edit, Save, X } from 'lucide-react';

const STATUS_CONFIG: Record<RoverStatus, { label: string; variant: BadgeProps['variant']; icon: React.ReactNode }> = {
  idle: { label: 'В ожидании', variant: 'default', icon: <Truck className="w-3 h-3" /> },
  delivering: { label: 'Доставка', variant: 'warning', icon: <Package className="w-3 h-3" /> },
  charging: { label: 'Зарядка', variant: 'success', icon: <Zap className="w-3 h-3" /> },
  broken: { label: 'Сломан', variant: 'destructive', icon: <AlertTriangle className="w-3 h-3" /> },
  returning: { label: 'Возвращение', variant: 'secondary', icon: <RotateCcw className="w-3 h-3" /> },
  lost: { label: 'Потерян', variant: 'destructive', icon: <AlertTriangle className="w-3 h-3" /> },
};

interface BadgeProps {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
}

export function RoverPanel() {
  const { rovers, selectedRoverId, setRovers } = useGameStore();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingRoverId, setEditingRoverId] = useState<number | null>(null);
  const [formData, setFormData] = useState<RoverCreate>({
    name: '',
    max_battery: 100,
    max_cargo: 50,
    speed: 10,
    efficiency: 1.0,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sortedRovers = useMemo(() =>
    [...rovers].sort((a, b) => {
      const statusOrder: Record<RoverStatus, number> = { delivering: 0, returning: 1, charging: 2, broken: 3, lost: 4, idle: 5 };
      return statusOrder[a.status] - statusOrder[b.status];
    }), [rovers]);

  const handleCreateRover = async () => {
    if (!formData.name.trim()) {
      setError('Введите имя ровера');
      return;
    }
    setIsCreating(true);
    setError(null);
    try {
      const newRover = await roversApi.create(formData);
      setRovers([...rovers, newRover]);
      setShowCreateDialog(false);
      setFormData({ name: '', max_battery: 100, max_cargo: 50, speed: 10, efficiency: 1.0 });
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка создания ровера');
    } finally {
      setIsCreating(false);
    }
  };

  const handleEditClick = (rover: Rover) => {
    setEditingRoverId(rover.id);
    setFormData({
      name: rover.name,
      max_battery: rover.max_battery,
      max_cargo: rover.max_cargo,
      speed: rover.speed,
      efficiency: rover.efficiency,
    });
  };

  const handleUpdateRover = async () => {
    if (!editingRoverId || !formData.name.trim()) {
      setError('Введите имя ровера');
      return;
    }
    setIsEditing(true);
    setError(null);
    try {
      const updatedRover = await roversApi.update(editingRoverId, formData);
      setRovers(rovers.map(r => r.id === editingRoverId ? updatedRover : r));
      setEditingRoverId(null);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка обновления ровера');
    } finally {
      setIsEditing(false);
    }
  };

  const cancelEdit = () => {
    setEditingRoverId(null);
    setError(null);
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <span>Роверы</span>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs">{rovers.length}</Badge>
            <Button variant="outline" size="icon" onClick={() => { setFormData({ name: '', max_battery: 100, max_cargo: 50, speed: 10, efficiency: 1.0 }); setShowCreateDialog(true); }} title="Создать ровер">
              <Plus className="w-4 h-4" />
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <div className="h-full overflow-y-auto">
          {sortedRovers.length === 0 ? (
            <div className="p-6 text-center text-moon-500">
              <Truck className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Нет роверов. Нажмите «+» чтобы создать первый.</p>
            </div>
          ) : (
            <div className="divide-y divide-moon-800">
              {sortedRovers.map(rover => (
                <RoverCard key={rover.id} rover={rover} isSelected={selectedRoverId === rover.id} editingRoverId={editingRoverId} onEdit={handleEditClick} />
              ))}
            </div>
          )}
        </div>
      </CardContent>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создать ровер</DialogTitle>
            <DialogDescription>
              Укажите параметры нового ровера. Он появится на базе.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm text-moon-400 mb-1">Имя</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ровер-Альфа"
                disabled={isCreating}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-moon-400 mb-1">Макс. батарея (%)</label>
                <Input
                  type="number"
                  value={formData.max_battery}
                  onChange={(e) => setFormData({ ...formData, max_battery: Number(e.target.value) })}
                  min="10"
                  max="500"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Грузоподъёмность (кг)</label>
                <Input
                  type="number"
                  value={formData.max_cargo}
                  onChange={(e) => setFormData({ ...formData, max_cargo: Number(e.target.value) })}
                  min="5"
                  max="200"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Скорость (км/ч)</label>
                <Input
                  type="number"
                  value={formData.speed}
                  onChange={(e) => setFormData({ ...formData, speed: Number(e.target.value) })}
                  min="1"
                  max="50"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Эффективность</label>
                <Input
                  type="number"
                  step="0.1"
                  value={formData.efficiency}
                  onChange={(e) => setFormData({ ...formData, efficiency: Number(e.target.value) })}
                  min="0.1"
                  max="2.0"
                  disabled={isCreating}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)} disabled={isCreating}>
              Отмена
            </Button>
            <Button onClick={handleCreateRover} disabled={isCreating}>
              {isCreating ? 'Создание...' : 'Создать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {editingRoverId && (
        <Dialog open onOpenChange={cancelEdit}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Редактировать ровер</DialogTitle>
              <DialogDescription>
                Измените параметры ровера. Изменения применятся сразу.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {error && (
                <div className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
                  {error}
                </div>
              )}
              <div>
                <label className="block text-sm text-moon-400 mb-1">Имя</label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  disabled={isEditing}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-moon-400 mb-1">Макс. батарея (%)</label>
                  <Input
                    type="number"
                    value={formData.max_battery}
                    onChange={(e) => setFormData({ ...formData, max_battery: Number(e.target.value) })}
                    min="10"
                    max="500"
                    disabled={isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm text-moon-400 mb-1">Грузоподъёмность (кг)</label>
                  <Input
                    type="number"
                    value={formData.max_cargo}
                    onChange={(e) => setFormData({ ...formData, max_cargo: Number(e.target.value) })}
                    min="5"
                    max="200"
                    disabled={isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm text-moon-400 mb-1">Скорость (км/ч)</label>
                  <Input
                    type="number"
                    value={formData.speed}
                    onChange={(e) => setFormData({ ...formData, speed: Number(e.target.value) })}
                    min="1"
                    max="50"
                    disabled={isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm text-moon-400 mb-1">Эффективность</label>
                  <Input
                    type="number"
                    step="0.1"
                    value={formData.efficiency}
                    onChange={(e) => setFormData({ ...formData, efficiency: Number(e.target.value) })}
                    min="0.1"
                    max="2.0"
                    disabled={isEditing}
                  />
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={cancelEdit} disabled={isEditing}>
                <X className="w-4 h-4 mr-1" /> Отмена
              </Button>
              <Button onClick={handleUpdateRover} disabled={isEditing}>
                {isEditing ? 'Сохранение...' : <> <Save className="w-4 h-4 mr-1" /> Сохранить </>}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
}

function RoverCard({ rover, isSelected, editingRoverId, onEdit }: { rover: Rover; isSelected: boolean; editingRoverId: number | null; onEdit: (rover: Rover) => void }) {
  const { setSelectedRover, setRovers } = useGameStore();
  const config = STATUS_CONFIG[rover.status];
  const batteryPct = rover.current_battery / rover.max_battery * 100;
  const batteryColor = batteryPct > 50 ? 'success' : batteryPct > 20 ? 'warning' : 'destructive';
  const isEditing = editingRoverId === rover.id;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={'p-4 transition-all cursor-pointer relative overflow-hidden ' + (isSelected ? 'bg-moon-800/50 border-l-2 border-moon-400' : '') + (isEditing ? ' ring-2 ring-moon-400' : '')}
      onClick={() => !isEditing && setSelectedRover(isSelected ? null : rover.id)}
      whileHover={{ backgroundColor: isSelected ? 'rgb(30 58 138 / 0.5)' : 'rgb(30 41 59 / 0.5)' }}
    >
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-moon-400/5 to-transparent opacity-0" style={{ transform: isSelected ? 'translateX(0)' : 'translateX(-100%)' }} />
      
      <div className="flex items-start justify-between gap-3 relative">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className={'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ' + (isSelected ? 'bg-moon-400/20 border border-moon-400' : 'bg-moon-800 border border-moon-700')}>
            {config.icon}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-moon-100 truncate">{rover.name}</h4>
              <Badge variant={config.variant} className="text-xs whitespace-nowrap">
                {config.icon} {config.label}
              </Badge>
            </div>
            <p className="text-xs text-moon-500 truncate mt-0.5">
              Позиция: ({rover.position_q}, {rover.position_r}) 
              {rover.status === 'delivering' && ` → Доставка`}
              {rover.status === 'returning' && ` → Возврат на базу`}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isEditing && (
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={(e) => { e.stopPropagation(); onEdit(rover); }}
              title="Редактировать"
            >
              <Edit className="w-4 h-4" />
            </Button>
          )}
          {rover.status === 'idle' && rover.position_q === 0 && rover.position_r === 0 && rover.current_battery < rover.max_battery && (
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={async (e) => { 
                e.stopPropagation(); 
                await roversApi.charge(rover.id); 
                const { rovers: currentRovers } = useGameStore.getState();
                setRovers(currentRovers.map(r => r.id === rover.id ? ({...r, current_battery: r.max_battery, status: 'idle' as const}) : r)); 
              }}
              title="Зарядить на базе"
            >
              <Zap className="w-4 h-4" />
            </Button>
          )}
          <Button 
            variant={rover.status === 'idle' ? 'default' : 'outline'} 
            size="sm" 
            className="h-8 px-2"
            onClick={(e) => { e.stopPropagation(); setSelectedRover(rover.id); }}
          >
            {rover.status === 'idle' ? 'Выбрать' : 'Детали'}
          </Button>
        </div>
      </div>

      <div className="mt-4 space-y-3 relative">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-moon-400">Батарея</span>
            <span className="font-mono text-moon-200">{Math.round(rover.current_battery)}%</span>
          </div>
          <Progress value={rover.current_battery} max={rover.max_battery} variant={batteryColor} className="h-1.5" />
        </div>
        
        {rover.current_cargo > 0 && (
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-moon-400 flex items-center gap-1"><Package className="w-3 h-3" /> Груз</span>
              <span className="font-mono text-moon-200">{rover.current_cargo.toFixed(1)} / {rover.max_cargo} кг</span>
            </div>
            <Progress value={rover.current_cargo} max={rover.max_cargo} variant="default" className="h-1.5" />
          </div>
        )}
        
        <div className="flex items-center justify-between text-xs text-moon-500 pt-1 border-t border-moon-800">
          <span>Доставок: <span className="text-moon-300 font-mono">{rover.deliveries_completed}</span></span>
          <span>Пробег: <span className="text-moon-300 font-mono">{rover.total_distance.toFixed(1)} км</span></span>
        </div>
      </div>

      {isSelected && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 pt-4 border-t border-moon-700 space-y-3"
        >
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-moon-800/50 rounded p-2">
              <div className="text-moon-500">Макс. батарея</div>
              <div className="font-mono text-moon-200">{rover.max_battery}%</div>
            </div>
            <div className="bg-moon-800/50 rounded p-2">
              <div className="text-moon-500">Грузоподъёмность</div>
              <div className="font-mono text-moon-200">{rover.max_cargo} кг</div>
            </div>
            <div className="bg-moon-800/50 rounded p-2">
              <div className="text-moon-500">Скорость</div>
              <div className="font-mono text-moon-200">{rover.speed} км/ч</div>
            </div>
            <div className="bg-moon-800/50 rounded p-2">
              <div className="text-moon-500">Эффективность</div>
              <div className="font-mono text-moon-200">{rover.efficiency}x</div>
            </div>
          </div>
          
          {rover.status === 'broken' && (
            <div className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
              <AlertTriangle className="w-4 h-4 inline mr-1" />
              Ровер требует ремонта. Верните на базу для восстановления.
            </div>
          )}
          
          {rover.status === 'charging' && (
            <div className="bg-green-900/30 border border-green-700 rounded p-3 text-sm text-green-300">
              <Zap className="w-4 h-4 inline mr-1" />
              Ровер заряжается на базе...
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}