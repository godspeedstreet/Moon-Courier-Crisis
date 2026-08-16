from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models import EventType, OrderStatus, RoverStatus, ZoneType


class ZoneBase(BaseModel):
    q: int
    r: int
    zone_type: ZoneType = ZoneType.SAFE
    risk_modifier: float = 1.0
    speed_modifier: float = 1.0
    name: str | None = None


class ZoneCreate(ZoneBase):
    pass


class ZoneResponse(ZoneBase):
    id: int

    class Config:
        from_attributes = True


class RoverBase(BaseModel):
    name: str
    max_battery: float = 100.0
    max_cargo: float = 50.0
    speed: float = 10.0
    efficiency: float = 1.0


class RoverCreate(RoverBase):
    pass


class RoverUpdate(BaseModel):
    current_battery: float | None = None
    current_cargo: float | None = None
    status: RoverStatus | None = None
    position_q: int | None = None
    position_r: int | None = None


class RoverResponse(RoverBase):
    id: int
    current_battery: float
    current_cargo: float
    status: RoverStatus
    position_q: int
    position_r: int
    base_q: int
    base_r: int
    deliveries_completed: int
    total_distance: float
    repair_days_left: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    title: str
    description: str | None = None
    weight: float = Field(gt=0)
    reward: float = Field(ge=0)
    urgency: int = Field(ge=1, le=5, default=1)
    risk_level: int = Field(ge=1, le=5, default=1)
    pickup_q: int
    pickup_r: int
    delivery_q: int
    delivery_r: int
    expires_day: int | None = None  # game-day deadline for urgent orders


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: int
    status: OrderStatus
    created_day: int = 1
    created_at: datetime
    assigned_rover_id: int | None = None
    assigned_at: datetime | None = None
    delivered_at: datetime | None = None

    class Config:
        from_attributes = True


class DeliveryCreate(BaseModel):
    rover_id: int
    order_id: int


class DeliveryResponse(BaseModel):
    id: int
    rover_id: int
    order_id: int
    started_at: datetime
    completed_at: datetime | None = None
    distance: float
    battery_consumed: float
    success: bool
    resolved: bool = False
    success_chance: float = 0.0
    failure_reason: str | None = None
    credits_earned: float
    path_taken: list[dict[str, int]] | None = None

    class Config:
        from_attributes = True


class GameEventBase(BaseModel):
    event_type: EventType
    day: int
    description: str
    data: dict[str, Any] | None = None


class GameEventCreate(GameEventBase):
    pass


class GameEventResponse(GameEventBase):
    id: int
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GameStateBase(BaseModel):
    current_day: int = 1
    max_days: int = 7
    credits: float = 1000.0
    base_rating: float = 100.0
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    rovers_lost: int = 0
    charge_bonus: float = 0.0
    dust_storm_active: bool = False
    is_game_over: bool = False
    game_over_reason: str | None = None
    won: bool = False


class GameStateResponse(GameStateBase):
    updated_at: datetime

    class Config:
        from_attributes = True


class DeliverySimulationRequest(BaseModel):
    rover_id: int
    order_id: int


class DeliverySimulationResponse(BaseModel):
    success: bool
    distance: float
    battery_needed: float
    time_estimate: float  # hours
    risk_score: float  # 0-1, chance of failure
    path: list[dict[str, int]]
    warnings: list[str] = []
    failure_reason: str | None = None
    success_chance: float = 0.95


class AssignOrderRequest(BaseModel):
    rover_id: int
    order_id: int


class NextDayRequest(BaseModel):
    pass


class NextDayResponse(BaseModel):
    day: int
    credits: float
    base_rating: float
    new_orders: list[OrderResponse]
    events: list[GameEventResponse]
    rover_updates: list[RoverResponse]
    messages: list[str] = []
    is_game_over: bool
    game_over_reason: str | None = None
    won: bool = False