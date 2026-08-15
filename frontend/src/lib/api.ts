import axios from 'axios';
import type {
  Zone, Rover, Order, Delivery, GameEvent, GameState,
  DeliverySimulationResponse, NextDayResponse, Stats
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Zones
export const zonesApi = {
  getAll: () => api.get<Zone[]>('/zones').then(r => r.data),
  generate: (radius = 8) => api.post<Zone[]>('/zones/generate', null, { params: { radius } }).then(r => r.data),
};

// Rovers
export const roversApi = {
  getAll: () => api.get<Rover[]>('/rovers').then(r => r.data),
  get: (id: number) => api.get<Rover>(`/rovers/${id}`).then(r => r.data),
  create: (data: Partial<Rover>) => api.post<Rover>('/rovers', data).then(r => r.data),
  update: (id: number, data: Partial<Rover>) => api.patch<Rover>(`/rovers/${id}`, data).then(r => r.data),
  charge: (id: number) => api.post<Rover>(`/rovers/${id}/charge`).then(r => r.data),
};

// Orders
export const ordersApi = {
  getAll: (status?: string) => api.get<Order[]>('/orders', { params: { status } }).then(r => r.data),
  get: (id: number) => api.get<Order>(`/orders/${id}`).then(r => r.data),
  create: (data: Partial<Order>) => api.post<Order>('/orders', data).then(r => r.data),
};

// Delivery
export const deliveryApi = {
  simulate: (roverId: number, orderId: number) => 
    api.post<DeliverySimulationResponse>('/delivery/simulate', { rover_id: roverId, order_id: orderId }).then(r => r.data),
  assign: (roverId: number, orderId: number) => 
    api.post<Delivery>('/delivery/assign', { rover_id: roverId, order_id: orderId }).then(r => r.data),
};

// Game State
export const gameApi = {
  getState: () => api.get<GameState>('/game/state').then(r => r.data),
  nextDay: () => api.post<NextDayResponse>('/game/next-day').then(r => r.data),
  reset: () => api.post('/game/reset').then(r => r.data),
  getStats: () => api.get<Stats>('/stats').then(r => r.data),
};

// Events
export const eventsApi = {
  getAll: () => api.get<GameEvent[]>('/events').then(r => r.data),
};

export default api;