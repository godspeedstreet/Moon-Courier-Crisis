import { useGameStore } from '../../store/gameStore';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ScrollArea } from '../ui/ScrollArea';
import { 
  AlertTriangle, Wind, Zap, Radio, 
  Skull, Shield, Info 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { GameEvent } from '../../types';

const EVENT_ICONS: Record<string, React.ReactNode> = {
  solar_flare: <Zap className="w-4 h-4 text-yellow-400" />,
  dust_storm: <Wind className="w-4 h-4 text-amber-400" />,
  rover_malfunction: <AlertTriangle className="w-4 h-4 text-red-400" />,
  priority_order: <Radio className="w-4 h-4 text-green-400" />,
  base_upgrade: <Shield className="w-4 h-4 text-blue-400" />,
  meteorite_impact: <Skull className="w-4 h-4 text-purple-400" />,
};

const EVENT_COLORS: Record<string, string> = {
  solar_flare: 'bg-yellow-500/10 border-yellow-500/20',
  dust_storm: 'bg-amber-500/10 border-amber-500/20',
  rover_malfunction: 'bg-red-500/10 border-red-500/20',
  priority_order: 'bg-green-500/10 border-green-500/20',
  base_upgrade: 'bg-blue-500/10 border-blue-500/20',
  meteorite_impact: 'bg-purple-500/10 border-purple-500/20',
};

export function EventLog() {
  const { events } = useGameStore();

  if (events.length === 0) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="w-5 h-5" />
            Журнал событий
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex items-center justify-center text-moon-500">
          <p>Событий пока нет. Они появятся по мере игры.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-5 h-5" />
            Журнал событий
          </div>
          <Badge variant="outline" className="text-xs">{events.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-3">
            <AnimatePresence mode="popLayout">
              {events.slice().reverse().map((event, index) => (
                <EventItem key={event.id} event={event} index={index} />
              ))}
            </AnimatePresence>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function EventItem({ event, index }: { event: GameEvent; index: number }) {
  const Icon = EVENT_ICONS[event.event_type] || <Info className="w-4 h-4" />;
  const colorClass = EVENT_COLORS[event.event_type] || 'bg-moon-800/50 border-moon-700';
  const dayStr = `День ${event.day}`;
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -20, height: 0 }}
      animate={{ opacity: 1, x: 0, height: 'auto' }}
      exit={{ opacity: 0, x: 20, height: 0 }}
      transition={{ delay: index * 0.05 }}
      className={'rounded-lg border p-3 transition-colors ' + colorClass}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 pt-0.5">{Icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-moon-100">{event.description}</span>
            <Badge variant="outline" className="text-xs text-moon-400">{dayStr}</Badge>
            {event.resolved && (
              <Badge variant="success" className="text-xs">Решено</Badge>
            )}
          </div>
          {event.data && Object.keys(event.data).length > 0 && (
            <EventDetails data={event.data} type={event.event_type} />
          )}
        </div>
      </div>
    </motion.div>
  );
}

function EventDetails({ data, type }: { data: Record<string, any>; type: string }) {
  const details: React.ReactNode[] = [];
  
  switch (type) {
    case 'rover_malfunction':
      if (data.rover_id) details.push(<DetailRow key="rover" label="Ровер ID" value={data.rover_id} />);
      if (data.repair_days) details.push(<DetailRow key="repair" label="Дней на ремонт" value={data.repair_days} />);
      break;
    case 'meteorite_impact':
      if (data.radius) details.push(<DetailRow key="radius" label="Радиус зоны" value={`${data.radius} гекс`} />);
      break;
    case 'priority_order':
      if (data.bonus_multiplier) details.push(<DetailRow key="bonus" label="Множитель награды" value={`${data.bonus_multiplier}x`} />);
      break;
    case 'base_upgrade':
      if (data.charge_bonus) details.push(<DetailRow key="charge" label="Бонус зарядки" value={`${(data.charge_bonus * 100).toFixed(0)}%`} />);
      break;
  }
  
  if (details.length === 0) return null;
  
  return (
    <div className="mt-2 pt-2 border-t border-current/20 grid grid-cols-2 gap-2 text-xs">
      {details}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: any }) {
  return (
    <div className="flex justify-between">
      <span className="text-moon-500">{label}</span>
      <span className="font-mono text-moon-300">{value}</span>
    </div>
  );
}