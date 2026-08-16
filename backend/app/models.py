import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ZoneType(str, enum.Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"
    IMPASSABLE = "impassable"


class RoverStatus(str, enum.Enum):
    IDLE = "idle"
    DELIVERING = "delivering"
    CHARGING = "charging"
    BROKEN = "broken"
    RETURNING = "returning"
    LOST = "lost"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


class EventType(str, enum.Enum):
    SOLAR_FLARE = "solar_flare"
    DUST_STORM = "dust_storm"
    ROVER_MALFUNCTION = "rover_malfunction"
    PRIORITY_ORDER = "priority_order"
    BASE_UPGRADE = "base_upgrade"
    METEORITE_IMPACT = "meteorite_impact"


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    q: Mapped[int] = mapped_column(Integer, index=True)  # hex axial coordinates
    r: Mapped[int] = mapped_column(Integer, index=True)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType), default=ZoneType.SAFE)
    risk_modifier: Mapped[float] = mapped_column(Float, default=1.0)  # multiplier for failure chance
    speed_modifier: Mapped[float] = mapped_column(Float, default=1.0)  # multiplier for travel time
    name: Mapped[str | None] = mapped_column(String, nullable=True)  # crater name, base name, etc.


class Rover(Base):
    __tablename__ = "rovers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    max_battery: Mapped[float] = mapped_column(Float, default=100.0)
    current_battery: Mapped[float] = mapped_column(Float, default=100.0)
    max_cargo: Mapped[float] = mapped_column(Float, default=50.0)  # kg
    current_cargo: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[RoverStatus] = mapped_column(Enum(RoverStatus), default=RoverStatus.IDLE)
    position_q: Mapped[int] = mapped_column(Integer, default=0)  # start at base (0,0)
    position_r: Mapped[int] = mapped_column(Integer, default=0)
    base_q: Mapped[int] = mapped_column(Integer, default=0)
    base_r: Mapped[int] = mapped_column(Integer, default=0)
    speed: Mapped[float] = mapped_column(Float, default=10.0)  # km/h base speed
    efficiency: Mapped[float] = mapped_column(Float, default=1.0)  # battery efficiency multiplier
    deliveries_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_distance: Mapped[float] = mapped_column(Float, default=0.0)
    repair_days_left: Mapped[int] = mapped_column(Integer, default=0)  # days of repair remaining when BROKEN
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deliveries: Mapped[list["Delivery"]] = relationship(back_populates="rover")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    weight: Mapped[float] = mapped_column(Float)  # kg
    reward: Mapped[float] = mapped_column(Float)  # credits
    urgency: Mapped[int] = mapped_column(Integer, default=1)  # 1-5, higher = more urgent
    risk_level: Mapped[int] = mapped_column(Integer, default=1)  # 1-5, higher = riskier
    pickup_q: Mapped[int] = mapped_column(Integer)
    pickup_r: Mapped[int] = mapped_column(Integer)
    delivery_q: Mapped[int] = mapped_column(Integer)
    delivery_r: Mapped[int] = mapped_column(Integer)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING)
    created_day: Mapped[int] = mapped_column(Integer, default=1)  # game day when the order appeared
    expires_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # game-day deadline for urgent orders
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    assigned_rover_id: Mapped[int | None] = mapped_column(ForeignKey("rovers.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    rover: Mapped[Optional["Rover"]] = relationship()
    delivery: Mapped[Optional["Delivery"]] = relationship(back_populates="order", uselist=False)


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rover_id: Mapped[int] = mapped_column(ForeignKey("rovers.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    distance: Mapped[float] = mapped_column(Float)  # total km
    battery_consumed: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)  # outcome rolled at the end of the day
    success_chance: Mapped[float] = mapped_column(Float, default=0.0)  # chance fixed at assignment time
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    credits_earned: Mapped[float] = mapped_column(Float, default=0.0)
    path_taken: Mapped[list[dict[str, int]] | None] = mapped_column(JSON, nullable=True)  # list of hex coordinates

    rover: Mapped["Rover"] = relationship(back_populates="deliveries")
    order: Mapped["Order"] = relationship(back_populates="delivery")


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType))
    day: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # event-specific data
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GameState(Base):
    __tablename__ = "game_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    current_day: Mapped[int] = mapped_column(Integer, default=1)
    max_days: Mapped[int] = mapped_column(Integer, default=7)
    credits: Mapped[float] = mapped_column(Float, default=1000.0)
    base_rating: Mapped[float] = mapped_column(Float, default=100.0)  # 0-100, game over if < 0
    total_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    successful_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    failed_deliveries: Mapped[int] = mapped_column(Integer, default=0)
    rovers_lost: Mapped[int] = mapped_column(Integer, default=0)
    charge_bonus: Mapped[float] = mapped_column(Float, default=0.0)  # stacking bonus from BASE_UPGRADE events
    dust_storm_active: Mapped[bool] = mapped_column(Boolean, default=False)  # DUST_STORM effect for the current day
    flare_zone: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # SOLAR_FLARE zone to restore next day
    is_game_over: Mapped[bool] = mapped_column(Boolean, default=False)
    game_over_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    won: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
