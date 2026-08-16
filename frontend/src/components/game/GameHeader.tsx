import { useGameStore } from '../../store/gameStore';
import { Card, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Progress } from '../ui/Progress';
import { Badge } from '../ui/Badge';
import { Sun, Coins, Star, AlertTriangle, RotateCcw, Trophy } from 'lucide-react';
import { motion } from 'framer-motion';
import { gameApi, zonesApi, ordersApi, eventsApi } from '../../lib/api';
import { toast } from '../../hooks/use-toast';

export function GameHeader() {
  const { gameState, rovers, setGameState, setRovers, setOrders, setEvents, setZones } = useGameStore();
  
  const day = gameState?.current_day || 1;
  const maxDays = gameState?.max_days || 7;
  const credits = gameState?.credits || 1000;
  const baseRating = gameState?.base_rating || 100;
  const isGameOver = gameState?.is_game_over || false;
  const won = gameState?.won || false;
  
  const dayProgress = (day / maxDays) * 100;
  const ratingColor = baseRating > 60 ? 'success' : baseRating > 30 ? 'warning' : 'destructive';
  const idleRovers = rovers.filter(r => r.status === 'idle').length;
  const busyRovers = rovers.length - idleRovers;

  if (!gameState) return null;

  const nextDay = async () => {
    if (!gameState || gameState.is_game_over) return;
    
    try {
      const data = await gameApi.nextDay();

      if (data) {
        const [updatedOrders, updatedEvents, updatedZones, updatedRovers, updatedState] = await Promise.all([
          ordersApi.getAll(),
          eventsApi.getAll(),
          zonesApi.getAll(),
          Promise.resolve(data.rover_updates),
          gameApi.getState(),
        ]);

        setGameState(updatedState);
        setOrders(updatedOrders);
        setEvents(updatedEvents);
        setZones(updatedZones);
        setRovers(updatedRovers);

        // Outcome of the day: deliveries, events, expiry
        (data.messages || []).slice(0, 4).forEach((msg, i) => {
          const bad = /провалена|просрочен|ПОТЕРЯН|сломан|ОКОНЧЕНА/i.test(msg);
          setTimeout(() => {
            toast({
              title: `День ${data.day}`,
              description: bad ? `⚠️ ${msg}` : msg,
            });
          }, i * 300);
        });
      }
    } catch (e) {
      console.error('Next day failed:', e);
    }
  };

  return (
    <Card className="w-full">
      <CardContent className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex-1 min-w-[200px] max-w-md">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sun className="w-5 h-5 text-yellow-400" />
                <span className="font-semibold text-lg">
                  День <span className="text-yellow-300">{day}</span> / {maxDays}
                </span>
                {won && <Trophy className="w-5 h-5 text-yellow-400 animate-bounce" />}
              </div>
              <Badge variant={day === maxDays ? 'warning' : 'default'} className="text-xs">
                {isGameOver ? (won ? 'Завершено' : 'Конец игры') : `${Math.round(dayProgress)}%`}
              </Badge>
            </div>
            <Progress value={day} max={maxDays} variant={won ? 'success' : 'default'} className="h-2" />
          </div>

          <div className="flex items-center gap-3 px-4 py-2 bg-moon-800/50 rounded-lg border border-moon-700">
            <div className="p-2 bg-yellow-500/20 rounded-lg">
              <Coins className="w-6 h-6 text-yellow-400" />
            </div>
            <div>
              <div className="text-xs text-moon-400">Кредиты</div>
              <div className="font-mono text-xl text-yellow-300">{credits.toLocaleString()} ₡</div>
            </div>
          </div>

          <div className="flex items-center gap-3 px-4 py-2 bg-moon-800/50 rounded-lg border border-moon-700">
            <div className={`p-2 rounded-lg ${ratingColor === 'success' ? 'bg-green-500/20' : ratingColor === 'warning' ? 'bg-yellow-500/20' : 'bg-red-500/20'}`}>
              <Star className={`w-6 h-6 ${ratingColor === 'success' ? 'text-green-400' : ratingColor === 'warning' ? 'text-yellow-400' : 'text-red-400'}`} />
            </div>
            <div>
              <div className="text-xs text-moon-400">Рейтинг базы</div>
              <div className="font-mono text-xl" style={{ color: ratingColor === 'success' ? '#22c55e' : ratingColor === 'warning' ? '#fbbf24' : '#ef4444' }}>
                {Math.round(baseRating)}%
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 px-4 py-2 bg-moon-800/50 rounded-lg border border-moon-700">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <RotateCcw className="w-6 h-6 text-blue-400" />
            </div>
            <div className="flex items-center gap-4">
              <div>
                <div className="text-xs text-moon-400">Свободно</div>
                <div className="font-mono text-lg text-green-400">{idleRovers}</div>
              </div>
              <div>
                <div className="text-xs text-moon-400">Занято</div>
                <div className="font-mono text-lg text-yellow-400">{busyRovers}</div>
              </div>
            </div>
          </div>

          <div className="ml-auto">
            <Button 
              size="lg" 
              onClick={nextDay} 
              disabled={isGameOver}
              className={'gap-2 ' + (isGameOver ? 'bg-moon-700 text-moon-500' : '')}
            >
              {isGameOver ? (
                <>
                  {won ? <Trophy className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                  {won ? 'Победа!' : 'Игра окончена'}
                </>
              ) : (
                <>
                  <Sun className="w-5 h-5" />
                  Следующий день
                </>
              )}
            </Button>
          </div>
        </div>

        {isGameOver && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 p-4 rounded-lg border text-center"
            style={{
              backgroundColor: won ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              borderColor: won ? '#22c55e' : '#ef4444',
              color: won ? '#22c55e' : '#ef4444'
            }}
          >
            <div className="font-semibold text-lg mb-1">
              {won ? '🎉 Миссия выполнена!' : '☠️ Миссия провалена'}
            </div>
            <div className="text-sm opacity-90">
              {gameState.game_over_reason || (won ? `Вы прошли ${maxDays} дней!` : 'Рейтинг базы упал до 0')}.
            </div>
            {won && (
              <div className="mt-2 text-sm">
                Итоговый счёт: <span className="font-mono text-yellow-300">{credits.toLocaleString()} ₡</span>
              </div>
            )}
          </motion.div>
        )}
      </CardContent>
    </Card>
  );
}