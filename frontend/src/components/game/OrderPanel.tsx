import { useMemo, useState } from 'react';
import type { Order, OrderStatus, OrderCreate } from '../../types';
import { useGameStore } from '../../store/gameStore';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableCaption } from '../ui/Table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/Select';
import { Input } from '../ui/Input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '../ui/Dialog';
import { ordersApi } from '../../lib/api';
import { Package, Filter, X, Plus } from 'lucide-react';

const STATUS_CONFIG: Record<OrderStatus, { label: string; variant: BadgeProps['variant']; color: string }> = {
  pending: { label: 'Ожидает', variant: 'default', color: '#64748b' },
  assigned: { label: 'Назначен', variant: 'secondary', color: '#3b82f6' },
  in_transit: { label: 'В пути', variant: 'warning', color: '#fbbf24' },
  delivered: { label: 'Доставлен', variant: 'success', color: '#22c55e' },
  failed: { label: 'Провален', variant: 'destructive', color: '#ef4444' },
  expired: { label: 'Просрочен', variant: 'outline', color: '#94a3b8' },
};

interface BadgeProps {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';
}

export function OrderPanel() {
  const { orders, selectedOrderId, setSelectedOrder, rovers, setShowSimulation, setSimulationResult, setOrders } = useGameStore();
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'urgency', direction: 'desc' });
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [formData, setFormData] = useState<OrderCreate>({
    title: '',
    description: '',
    weight: 10,
    reward: 100,
    urgency: 1,
    risk_level: 1,
    pickup_q: 0,
    pickup_r: 0,
    delivery_q: 0,
    delivery_r: 0,
  });
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateOrder = async () => {
    if (!formData.title.trim()) {
      setError('Введите название заказа');
      return;
    }
    if (formData.pickup_q === formData.delivery_q && formData.pickup_r === formData.delivery_r) {
      setError('Точки забора и доставки не могут совпадать');
      return;
    }
    setIsCreating(true);
    setError(null);
    try {
      const newOrder = await ordersApi.create(formData);
      setOrders([...orders, newOrder]);
      setShowCreateDialog(false);
      setFormData({ title: '', description: '', weight: 10, reward: 100, urgency: 1, risk_level: 1, pickup_q: 0, pickup_r: 0, delivery_q: 0, delivery_r: 0 });
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка создания заказа');
    } finally {
      setIsCreating(false);
    }
  };

  const filteredOrders = useMemo(() => {
    let result = [...orders];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(o => 
        o.title.toLowerCase().includes(q) ||
        o.description?.toLowerCase().includes(q)
      );
    }

    if (statusFilter !== 'all') {
      result = result.filter(o => o.status === statusFilter);
    }

    result.sort((a, b) => {
      let aVal: any = a[sortConfig.key as keyof Order];
      let bVal: any = b[sortConfig.key as keyof Order];
      
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }
      
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [orders, searchQuery, statusFilter, sortConfig]);

  const handleSort = (key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const pendingCount = orders.filter(o => o.status === 'pending').length;
  const activeCount = orders.filter(o => o.status === 'in_transit' || o.status === 'assigned').length;

  return (
    <>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Package className="w-5 h-5" />
                Заказы
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">{pendingCount} в ожидании</Badge>
              <Badge variant="warning" className="text-xs">{activeCount} в работе</Badge>
              <Button variant="outline" size="icon" onClick={() => setShowCreateDialog(true)} title="Создать заказ">
                <Plus className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 overflow-hidden p-0">
          <div className="h-full flex flex-col">
            <div className="p-4 border-b border-moon-800 bg-moon-900/50 flex flex-col gap-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="relative flex-1 min-w-[200px] max-w-xs">
                  <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-moon-500" />
                  <Input
                    placeholder="Поиск по названию/описанию..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter as any}>
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="Статус" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все статусы</SelectItem>
                    <SelectItem value="pending">Ожидает</SelectItem>
                    <SelectItem value="assigned">Назначен</SelectItem>
                    <SelectItem value="in_transit">В пути</SelectItem>
                    <SelectItem value="delivered">Доставлен</SelectItem>
                    <SelectItem value="failed">Провален</SelectItem>
                    <SelectItem value="expired">Просрочен</SelectItem>
                  </SelectContent>
                </Select>
                {(searchQuery || statusFilter !== 'all') && (
                  <Button variant="ghost" size="sm" onClick={() => { setSearchQuery(''); setStatusFilter('all'); }}>
                    <X className="w-4 h-4 mr-1" /> Сбросить
                  </Button>
                )}
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-auto max-h-full">
              <Table>
                <TableCaption className="p-4 text-left text-xs text-moon-500">
                  {filteredOrders.length} из {orders.length} заказов
                </TableCaption>
                <TableHeader>
                  <TableRow className="border-b border-moon-700">
                    <TableHead className="cursor-pointer hover:bg-moon-800" onClick={() => handleSort('title')}>
                      Заказ {sortConfig.key === 'title' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-moon-800 text-right" onClick={() => handleSort('weight')}>
                      Вес {sortConfig.key === 'weight' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-moon-800 text-right" onClick={() => handleSort('reward')}>
                      Награда {sortConfig.key === 'reward' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-moon-800 text-center" onClick={() => handleSort('urgency')}>
                      Срочность {sortConfig.key === 'urgency' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-moon-800 text-center" onClick={() => handleSort('risk_level')}>
                      Риск {sortConfig.key === 'risk_level' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                    </TableHead>
                    <TableHead className="text-right">Расстояние</TableHead>
                    <TableHead>Статус</TableHead>
                    <TableHead className="w-24"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOrders.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-moon-500">
                        Заказы не найдены
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredOrders.map(order => (
                      <OrderRow 
                        key={order.id} 
                        order={order} 
                        isSelected={selectedOrderId === order.id}
                        rovers={rovers}
                        onSelect={setSelectedOrder}
                        onSimulate={setShowSimulation}
                        onSimulateResult={setSimulationResult}
                      />
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </CardContent>
      </Card>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Создать заказ</DialogTitle>
            <DialogDescription>
              Укажите параметры заказа. Он появится в списке доступных.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded p-3 text-sm text-red-300">
                {error}
              </div>
            )}
            <div>
              <label className="block text-sm text-moon-400 mb-1">Название</label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Доставка груза в сектор..."
                disabled={isCreating}
              />
            </div>
            <div>
              <label className="block text-sm text-moon-400 mb-1">Описание</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Опционально"
                disabled={isCreating}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-moon-400 mb-1">Вес (кг)</label>
                <Input
                  type="number"
                  value={formData.weight}
                  onChange={(e) => setFormData({ ...formData, weight: Number(e.target.value) })}
                  min="1"
                  max="200"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Награда (₡)</label>
                <Input
                  type="number"
                  value={formData.reward}
                  onChange={(e) => setFormData({ ...formData, reward: Number(e.target.value) })}
                  min="10"
                  max="10000"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Срочность (1-5)</label>
                <Input
                  type="number"
                  value={formData.urgency}
                  onChange={(e) => setFormData({ ...formData, urgency: Number(e.target.value) })}
                  min="1"
                  max="5"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Риск (1-5)</label>
                <Input
                  type="number"
                  value={formData.risk_level}
                  onChange={(e) => setFormData({ ...formData, risk_level: Number(e.target.value) })}
                  min="1"
                  max="5"
                  disabled={isCreating}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-moon-400 mb-1">Забор: q</label>
                <Input
                  type="number"
                  value={formData.pickup_q}
                  onChange={(e) => setFormData({ ...formData, pickup_q: Number(e.target.value) })}
                  min="-8"
                  max="8"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Забор: r</label>
                <Input
                  type="number"
                  value={formData.pickup_r}
                  onChange={(e) => setFormData({ ...formData, pickup_r: Number(e.target.value) })}
                  min="-8"
                  max="8"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Доставка: q</label>
                <Input
                  type="number"
                  value={formData.delivery_q}
                  onChange={(e) => setFormData({ ...formData, delivery_q: Number(e.target.value) })}
                  min="-8"
                  max="8"
                  disabled={isCreating}
                />
              </div>
              <div>
                <label className="block text-sm text-moon-400 mb-1">Доставка: r</label>
                <Input
                  type="number"
                  value={formData.delivery_r}
                  onChange={(e) => setFormData({ ...formData, delivery_r: Number(e.target.value) })}
                  min="-8"
                  max="8"
                  disabled={isCreating}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)} disabled={isCreating}>
              Отмена
            </Button>
            <Button onClick={handleCreateOrder} disabled={isCreating}>
              {isCreating ? 'Создание...' : 'Создать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

function OrderRow({ 
  order, 
  isSelected, 
  rovers, 
  onSelect, 
  onSimulate, 
  onSimulateResult 
}: { 
  order: Order; 
  isSelected: boolean; 
  rovers: any[];
  onSelect: (id: number | null) => void;
  onSimulate: (show: boolean) => void;
  onSimulateResult: (result: any) => void;
}) {
  const config = STATUS_CONFIG[order.status];
  const availableRovers = rovers.filter(r => r.status === 'idle' && r.max_cargo >= order.weight);
  const distance = Math.abs(order.pickup_q) + Math.abs(order.pickup_r) + Math.abs(order.delivery_q - order.pickup_q) + Math.abs(order.delivery_r - order.pickup_r);

  const handleClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    onSelect(isSelected ? null : order.id);
  };

  const handleSimulate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (availableRovers.length === 0) return;
    onSimulateResult({ order, rovers: availableRovers });
    onSimulate(true);
  };

  const urgencyStars = '★'.repeat(order.urgency) + '☆'.repeat(5 - order.urgency);
  const riskStars = '⚠'.repeat(order.risk_level);

  return (
    <TableRow
      className={'transition-colors cursor-pointer ' + 
        (isSelected ? 'bg-moon-800/50' : '') + 
        (order.status === 'pending' ? ' hover:bg-moon-800/30' : '') + 
        (order.urgency >= 4 ? ' border-l-2 border-yellow-500' : '')
      }
      onClick={handleClick}
    >
      <TableCell className="font-mono text-sm">
        <div className="font-medium text-moon-100">{order.title}</div>
        <div className="text-xs text-moon-500 truncate max-w-[200px]">{order.description}</div>
      </TableCell>
      <TableCell className="text-right font-mono">
        <span className="flex items-center justify-end gap-1">
          <Package className="w-3 h-3" />
          {order.weight.toFixed(1)} кг
        </span>
      </TableCell>
      <TableCell className="text-right font-mono text-yellow-300">
        {order.reward.toFixed(0)} ₡
      </TableCell>
      <TableCell className="text-center text-xs font-mono text-yellow-400" title={`Срочность: ${order.urgency}/5`}>
        {urgencyStars}
      </TableCell>
      <TableCell className="text-center text-xs font-mono text-red-400" title={`Риск: ${order.risk_level}/5`}>
        {riskStars}
      </TableCell>
      <TableCell className="text-right text-xs text-moon-500 font-mono">
        ~{distance} км
      </TableCell>
      <TableCell>
        <Badge variant={config.variant} className="capitalize">{config.label}</Badge>
      </TableCell>
      <TableCell className="text-right">
        {order.status === 'pending' && availableRovers.length > 0 && (
          <Button variant="outline" size="sm" onClick={handleSimulate} className="h-8 px-2">
            Отправить
          </Button>
        )}
        {order.status === 'pending' && availableRovers.length === 0 && (
          <Badge variant="destructive" className="text-xs">Нет роверов</Badge>
        )}
        {order.status === 'in_transit' && (
          <Badge variant="warning" className="text-xs">В пути</Badge>
        )}
        {order.status === 'assigned' && (
          <Badge variant="secondary" className="text-xs">Назначен</Badge>
        )}
      </TableCell>
    </TableRow>
  );
}