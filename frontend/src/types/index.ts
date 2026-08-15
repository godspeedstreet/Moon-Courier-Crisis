export type ZoneType = 'safe' | 'moderate' | 'dangerous' | 'impassable';

export interface Zone {
  id: number;
  q: number;
  r: number;
  zone_type: ZoneType;
  risk_modifier: number;
  speed_modifier: number;
  name?: string;
}

export type RoverStatus = 'idle' | 'delivering' | 'charging' | 'broken' | 'returning';

export interface Rover {
  id: number;
  name: string;
  max_battery: number;
  current_battery: number;
  max_cargo: number;
  current_cargo: number;
  status: RoverStatus;
  position_q: number;
  position_r: number;
  base_q: number;
  base_r: number;
  speed: number;
  efficiency: number;
  deliveries_completed: number;
  total_distance: number;
  created_at: string;
  updated_at: string;
}

export interface RoverCreate {
  name: string;
  max_battery: number;
  max_cargo: number;
  speed: number;
  efficiency: number;
}

export interface RoverUpdate {
  name?: string;
  max_battery?: number;
  max_cargo?: number;
  speed?: number;
  efficiency?: number;
}

export interface OrderCreate {
  title: string;
  description?: string;
  weight: number;
  reward: number;
  urgency: number;
  risk_level: number;
  pickup_q: number;
  pickup_r: number;
  delivery_q: number;
  delivery_r: number;
}

export type OrderStatus = 'pending' | 'assigned' | 'in_transit' | 'delivered' | 'failed' | 'expired';

export interface Order {
  id: number;
  title: string;
  description?: string;
  weight: number;
  reward: number;
  urgency: number;
  risk_level: number;
  pickup_q: number;
  pickup_r: number;
  delivery_q: number;
  delivery_r: number;
  status: OrderStatus;
  expires_at?: string;
  created_at: string;
  assigned_rover_id?: number;
  assigned_at?: string;
  delivered_at?: string;
}

export interface Delivery {
  id: number;
  rover_id: number;
  order_id: number;
  started_at: string;
  completed_at?: string;
  distance: number;
  battery_consumed: number;
  success: boolean;
  failure_reason?: string;
  credits_earned: number;
  path_taken?: Array<{ q: number; r: number }>;
}

export type EventType = 'solar_flare' | 'dust_storm' | 'rover_malfunction' | 'priority_order' | 'base_upgrade' | 'meteorite_impact';

export interface GameEvent {
  id: number;
  event_type: EventType;
  day: number;
  description: string;
  data?: Record<string, unknown>;
  resolved: boolean;
  created_at: string;
}

export interface GameState {
  current_day: number;
  max_days: number;
  credits: number;
  base_rating: number;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  rovers_lost: number;
  is_game_over: boolean;
  game_over_reason?: string;
  won: boolean;
  updated_at: string;
}

export interface DeliverySimulationResponse {
  success: boolean;
  distance: number;
  battery_needed: number;
  time_estimate: number;
  risk_score: number;
  path: Array<{ q: number; r: number }>;
  warnings: string[];
  failure_reason?: string;
  success_chance?: number;
}

export interface NextDayResponse {
  day: number;
  credits: number;
  base_rating: number;
  new_orders: Order[];
  events: GameEvent[];
  rover_updates: Rover[];
  is_game_over: boolean;
  game_over_reason?: string;
  won: boolean;
}

export interface Stats {
  game_state: GameState;
  rovers_count: number;
  active_rovers: number;
  total_deliveries: number;
  successful_deliveries: number;
  pending_orders: number;
  total_credits_earned: number;
  total_distance: number;
}

export interface HexCoord {
  q: number;
  r: number;
}