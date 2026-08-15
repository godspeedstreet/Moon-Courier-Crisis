import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
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

    id = Column(Integer, primary_key=True, index=True)
    q = Column(Integer, index=True)  # hex axial coordinates
    r = Column(Integer, index=True)
    zone_type = Column(Enum(ZoneType), default=ZoneType.SAFE)
    risk_modifier = Column(Float, default=1.0)  # multiplier for failure chance
    speed_modifier = Column(Float, default=1.0)  # multiplier for travel time
    name = Column(String, nullable=True)  # crater name, base name, etc.


class Rover(Base):
    __tablename__ = "rovers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    max_battery = Column(Float, default=100.0)
    current_battery = Column(Float, default=100.0)
    max_cargo = Column(Float, default=50.0)  # kg
    current_cargo = Column(Float, default=0.0)
    status = Column(Enum(RoverStatus), default=RoverStatus.IDLE)
    position_q = Column(Integer, default=0)  # start at base (0,0)
    position_r = Column(Integer, default=0)
    base_q = Column(Integer, default=0)
    base_r = Column(Integer, default=0)
    speed = Column(Float, default=10.0)  # km/h base speed
    efficiency = Column(Float, default=1.0)  # battery efficiency multiplier
    deliveries_completed = Column(Integer, default=0)
    total_distance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deliveries = relationship("Delivery", back_populates="rover")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    weight = Column(Float)  # kg
    reward = Column(Float)  # credits
    urgency = Column(Integer, default=1)  # 1-5, higher = more urgent
    risk_level = Column(Integer, default=1)  # 1-5, higher = riskier
    pickup_q = Column(Integer)
    pickup_r = Column(Integer)
    delivery_q = Column(Integer)
    delivery_r = Column(Integer)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    expires_at = Column(DateTime, nullable=True)  # for urgent orders
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_rover_id = Column(Integer, ForeignKey("rovers.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    rover = relationship("Rover")
    delivery = relationship("Delivery", back_populates="order", uselist=False)


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    rover_id = Column(Integer, ForeignKey("rovers.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    distance = Column(Float)  # total km
    battery_consumed = Column(Float, default=0.0)
    success = Column(Boolean, default=False)
    failure_reason = Column(String, nullable=True)
    credits_earned = Column(Float, default=0.0)
    path_taken = Column(JSON, nullable=True)  # list of hex coordinates

    rover = relationship("Rover", back_populates="deliveries")
    order = relationship("Order", back_populates="delivery")


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(Enum(EventType))
    day = Column(Integer)
    description = Column(String)
    data = Column(JSON, nullable=True)  # event-specific data
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GameState(Base):
    __tablename__ = "game_state"

    id = Column(Integer, primary_key=True, default=1)
    current_day = Column(Integer, default=1)
    max_days = Column(Integer, default=7)
    credits = Column(Float, default=1000.0)
    base_rating = Column(Float, default=100.0)  # 0-100, game over if < 0
    total_deliveries = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    failed_deliveries = Column(Integer, default=0)
    rovers_lost = Column(Integer, default=0)
    is_game_over = Column(Boolean, default=False)
    game_over_reason = Column(String, nullable=True)
    won = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)