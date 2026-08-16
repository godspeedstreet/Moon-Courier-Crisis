import { useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import { zonesApi, roversApi, gameApi, ordersApi, eventsApi } from '../../lib/api';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/Tabs';
import { Button } from '../ui/Button';
import { HexMap } from './HexMap';
import { RoverPanel } from './RoverPanel';
import { OrderPanel } from './OrderPanel';
import { EventLog } from './EventLog';
import { SimulationModal } from './SimulationModal';
import { GameHeader } from './GameHeader';
import { Map, Truck, Package, List, Settings, RotateCcw } from 'lucide-react';

type TabValue = 'map' | 'rovers' | 'orders' | 'events';

export function GameLayout() {
const {
    activeTab, setActiveTab,
    rovers, simulationResult, showSimulation, setShowSimulation,
    setZones, setRovers, setGameState, setOrders, setEvents,
  } = useGameStore();

  useEffect(() => {
    async function loadInitialData() {
      try {
        const [zonesData, roversData, ordersData, eventsData, stateData] = await Promise.all([
          zonesApi.getAll(),
          roversApi.getAll(),
          ordersApi.getAll(),
          eventsApi.getAll(),
          gameApi.getState(),
        ]);
        setZones(zonesData);
        setRovers(roversData);
        setOrders(ordersData);
        setEvents(eventsData);
        setGameState(stateData);
      } catch (e) {
        console.error('Failed to load initial data:', e);
      }
    }
    loadInitialData();
  }, [setZones, setRovers, setOrders, setEvents, setGameState]);

  const handleGenerateMap = async () => {
    try {
      await zonesApi.generate(8);
      window.location.reload();
    } catch (e) {
      console.error('Failed to generate map:', e);
    }
  };

  const handleResetGame = async () => {
    if (!confirm('Сбросить игру? Все прогресс будет потерян.')) return;
    try {
      await gameApi.reset();
      window.location.reload();
    } catch (e) {
      console.error('Failed to reset game:', e);
    }
  };

  return (
    <div className="h-screen w-full flex flex-col bg-moon-950">
      <GameHeader />
      
      <div className="flex-1 flex overflow-hidden">
        <div className="w-full lg:w-2/3 flex flex-col min-w-0">
          <div className="h-full lg:h-[calc(100%-80px)] relative">
            <HexMap width={800} height={600} />
          </div>
          
          <div className="p-3 border-t border-moon-800 bg-moon-900/50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as TabValue)} className="w-auto">
                <TabsList>
                  <TabsTrigger value="map" className="px-3">
                    <Map className="w-4 h-4 mr-1" /> Карта
                  </TabsTrigger>
                  <TabsTrigger value="rovers" className="px-3">
                    <Truck className="w-4 h-4 mr-1" /> Роверы
                  </TabsTrigger>
                  <TabsTrigger value="orders" className="px-3">
                    <Package className="w-4 h-4 mr-1" /> Заказы
                  </TabsTrigger>
                  <TabsTrigger value="events" className="px-3">
                    <List className="w-4 h-4 mr-1" /> События
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleGenerateMap}>
                <RotateCcw className="w-4 h-4 mr-1" /> Новая карта
              </Button>
              <Button variant="ghost" size="sm" onClick={handleResetGame}>
                <Settings className="w-4 h-4 mr-1" /> Сброс
              </Button>
            </div>
          </div>
        </div>

        <div className="hidden lg:flex lg:w-1/3 flex-col border-l border-moon-800 min-w-0">
          <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as TabValue)} className="flex-1 flex flex-col">
            <TabsList className="flex-row border-b border-moon-800">
              <TabsTrigger value="rovers">
                <Truck className="w-4 h-4 mr-1" /> Роверы
              </TabsTrigger>
              <TabsTrigger value="orders">
                <Package className="w-4 h-4 mr-1" /> Заказы
              </TabsTrigger>
              <TabsTrigger value="events">
                <List className="w-4 h-4 mr-1" /> События
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="rovers" className="flex-1 overflow-hidden">
              <RoverPanel />
            </TabsContent>
            
            <TabsContent value="orders" className="flex-1 overflow-hidden">
              <OrderPanel />
            </TabsContent>
            
            <TabsContent value="events" className="flex-1 overflow-hidden">
              <EventLog />
            </TabsContent>
          </Tabs>
        </div>
      </div>

      <SimulationModal
        open={showSimulation}
        onOpenChange={setShowSimulation}
        order={simulationResult?.order || null}
        rovers={simulationResult?.rovers || rovers}
        onConfirm={() => setShowSimulation(false)}
      />

      <MobileBottomSheets />
    </div>
  );
}

function MobileBottomSheets() {
  const { activeTab, setActiveTab } = useGameStore();
  
  if (typeof window !== 'undefined' && window.innerWidth >= 1024) return null;

  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50">
      <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as TabValue)} className="bg-moon-900 border-t border-moon-800 rounded-t-2xl shadow-2xl">
        <TabsList className="grid grid-cols-3 p-2 bg-moon-950 rounded-t-2xl">
          <TabsTrigger value="rovers" className="py-2">
            <Truck className="w-5 h-5 mx-auto" />
          </TabsTrigger>
          <TabsTrigger value="orders" className="py-2">
            <Package className="w-5 h-5 mx-auto" />
          </TabsTrigger>
          <TabsTrigger value="events" className="py-2">
            <List className="w-5 h-5 mx-auto" />
          </TabsTrigger>
        </TabsList>
        
        <TabsContent value="rovers" className="p-4 max-h-[60vh] overflow-auto">
          <RoverPanel />
        </TabsContent>
        <TabsContent value="orders" className="p-4 max-h-[60vh] overflow-auto">
          <OrderPanel />
        </TabsContent>
        <TabsContent value="events" className="p-4 max-h-[60vh] overflow-auto">
          <EventLog />
        </TabsContent>
      </Tabs>
    </div>
  );
}