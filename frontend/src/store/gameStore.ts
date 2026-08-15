import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Rover, Order, GameState, GameEvent, Zone, Delivery, HexCoord } from '../types';

interface GameStore {
  // Data
  zones: Zone[];
  rovers: Rover[];
  orders: Order[];
  deliveries: Delivery[];
  events: GameEvent[];
  gameState: GameState | null;
  stats: any;
  
  // UI State
  selectedRoverId: number | null;
  selectedOrderId: number | null;
  hoveredHex: HexCoord | null;
  mapCenter: HexCoord;
  mapZoom: number;
  showSimulation: boolean;
  simulationResult: any;
  activeTab: 'map' | 'rovers' | 'orders' | 'events' | 'stats';
  
  // Actions
  setZones: (zones: Zone[]) => void;
  setRovers: (rovers: Rover[]) => void;
  setOrders: (orders: Order[]) => void;
  setDeliveries: (deliveries: Delivery[]) => void;
  setEvents: (events: GameEvent[]) => void;
  setGameState: (state: GameState) => void;
  setStats: (stats: any) => void;
  
  updateRover: (rover: Rover) => void;
  updateOrder: (order: Order) => void;
  addDelivery: (delivery: Delivery) => void;
  addEvent: (event: GameEvent) => void;
  
  setSelectedRover: (id: number | null) => void;
  setSelectedOrder: (id: number | null) => void;
  setHoveredHex: (hex: HexCoord | null) => void;
  setMapCenter: (center: HexCoord) => void;
  setMapZoom: (zoom: number) => void;
  setShowSimulation: (show: boolean) => void;
  setSimulationResult: (result: any) => void;
  setActiveTab: (tab: GameStore['activeTab']) => void;
  
  reset: () => void;
}

const initialState = {
  zones: [],
  rovers: [],
  orders: [],
  deliveries: [],
  events: [],
  gameState: null,
  stats: null,
  selectedRoverId: null,
  selectedOrderId: null,
  hoveredHex: null,
  mapCenter: { q: 0, r: 0 },
  mapZoom: 1,
  showSimulation: false,
  simulationResult: null,
  activeTab: 'map' as const,
};

export const useGameStore = create<GameStore>()(
  persist(
    (set) => ({
      ...initialState,
      
      setZones: (zones) => set({ zones }),
      setRovers: (rovers) => set({ rovers }),
      setOrders: (orders) => set({ orders }),
      setDeliveries: (deliveries) => set({ deliveries }),
      setEvents: (events) => set({ events }),
      setGameState: (gameState) => set({ gameState }),
      setStats: (stats) => set({ stats }),
      
      updateRover: (rover) => set((state) => ({
        rovers: state.rovers.map(r => r.id === rover.id ? rover : r)
      })),
      updateOrder: (order) => set((state) => ({
        orders: state.orders.map(o => o.id === order.id ? order : o)
      })),
      addDelivery: (delivery) => set((state) => ({
        deliveries: [delivery, ...state.deliveries]
      })),
      addEvent: (event) => set((state) => ({
        events: [event, ...state.events]
      })),
      
      setSelectedRover: (selectedRoverId) => set({ selectedRoverId }),
      setSelectedOrder: (selectedOrderId) => set({ selectedOrderId }),
      setHoveredHex: (hoveredHex) => set({ hoveredHex }),
      setMapCenter: (mapCenter) => set({ mapCenter }),
      setMapZoom: (mapZoom) => set({ mapZoom }),
      setShowSimulation: (showSimulation) => set({ showSimulation }),
      setSimulationResult: (simulationResult) => set({ simulationResult }),
      setActiveTab: (activeTab) => set({ activeTab }),
      
      reset: () => set(initialState),
    }),
    {
      name: 'moon-courier-game',
      partialize: (state) => ({
        mapCenter: state.mapCenter,
        mapZoom: state.mapZoom,
        activeTab: state.activeTab,
      }),
    }
  )
);