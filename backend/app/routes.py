from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import random

from app.database import get_db
from app.models import (
    Zone, Rover, Order, Delivery, GameEvent, GameState,
    ZoneType, RoverStatus, OrderStatus, EventType
)
from app.schemas import (
    ZoneResponse, RoverCreate, RoverUpdate, RoverResponse,
    OrderCreate, OrderResponse, DeliveryResponse, DeliverySimulationResponse,
    GameEventResponse, GameStateResponse, NextDayResponse,
    AssignOrderRequest, DeliverySimulationRequest
)
from app.game_logic import (
    calculate_delivery, can_deliver, generate_orders, generate_random_event,
    apply_event, next_day_logic, Hex, a_star_search, generate_moon_map, ZONE_MODIFIERS
)
from app.hex_utils import ZoneType as HexZoneType
from app.seed import seed_initial_data

router = APIRouter()


def _persist_zone_updates(db: Session, zone_updates: dict) -> None:
    """Save zone type changes from events back to the database."""
    for (q, r), zone_type in zone_updates.items():
        zone = db.query(Zone).filter(Zone.q == q, Zone.r == r).first()
        if not zone:
            continue
        modifiers = ZONE_MODIFIERS[zone_type]
        zone.zone_type = zone_type
        zone.risk_modifier = modifiers.risk_multiplier
        zone.speed_modifier = modifiers.speed_multiplier


# ---------- Zones ----------
@router.get("/zones", response_model=List[ZoneResponse])
def get_zones(db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    return zones


@router.post("/zones/generate", response_model=List[ZoneResponse])
def generate_zones(radius: int = 8, db: Session = Depends(get_db)):
    """Generate procedural moon map."""
    db.query(Zone).delete()
    db.commit()
    
    zone_data = generate_moon_map(radius)
    zones = []
    for (q, r), zone_type in zone_data.items():
        modifiers = ZONE_MODIFIERS[zone_type]
        zone = Zone(
            q=q, r=r, zone_type=zone_type,
            risk_modifier=modifiers.risk_multiplier,
            speed_modifier=modifiers.speed_multiplier,
        )
        db.add(zone)
        zones.append(zone)
    
    db.commit()
    for z in zones:
        db.refresh(z)
    return zones


# ---------- Rovers ----------
@router.get("/rovers", response_model=List[RoverResponse])
def get_rovers(db: Session = Depends(get_db)):
    return db.query(Rover).all()


@router.post("/rovers", response_model=RoverResponse)
def create_rover(rover: RoverCreate, db: Session = Depends(get_db)):
    # Check if rover with name exists
    existing = db.query(Rover).filter(Rover.name == rover.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ровер с таким именем уже существует")
    
    db_rover = Rover(**rover.model_dump())
    db.add(db_rover)
    db.commit()
    db.refresh(db_rover)
    return db_rover


@router.get("/rovers/{rover_id}", response_model=RoverResponse)
def get_rover(rover_id: int, db: Session = Depends(get_db)):
    rover = db.query(Rover).filter(Rover.id == rover_id).first()
    if not rover:
        raise HTTPException(status_code=404, detail="Ровер не найден")
    return rover


@router.patch("/rovers/{rover_id}", response_model=RoverResponse)
def update_rover(rover_id: int, update: RoverUpdate, db: Session = Depends(get_db)):
    rover = db.query(Rover).filter(Rover.id == rover_id).first()
    if not rover:
        raise HTTPException(status_code=404, detail="Ровер не найден")
    
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(rover, field, value)
    
    rover.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rover)
    return rover


@router.post("/rovers/{rover_id}/charge", response_model=RoverResponse)
def charge_rover(rover_id: int, db: Session = Depends(get_db)):
    rover = db.query(Rover).filter(Rover.id == rover_id).first()
    if not rover:
        raise HTTPException(status_code=404, detail="Ровер не найден")
    
    if rover.position_q != rover.base_q or rover.position_r != rover.base_r:
        raise HTTPException(status_code=400, detail="Ровер не на базе")
    
    rover.current_battery = rover.max_battery
    rover.status = RoverStatus.IDLE
    rover.current_cargo = 0
    rover.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rover)
    return rover


# ---------- Orders ----------
@router.get("/orders", response_model=List[OrderResponse])
def get_orders(
    status: Optional[OrderStatus] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    return query.order_by(Order.created_at.desc()).all()


@router.post("/orders", response_model=OrderResponse)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    db_order = Order(**order.model_dump())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


# ---------- Delivery Simulation ----------
@router.post("/delivery/simulate", response_model=DeliverySimulationResponse)
def simulate_delivery(request: DeliverySimulationRequest, db: Session = Depends(get_db)):
    rover = db.query(Rover).filter(Rover.id == request.rover_id).first()
    order = db.query(Order).filter(Order.id == request.order_id).first()
    
    if not rover:
        raise HTTPException(status_code=404, detail="Ровер не найден")
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    zones = {(z.q, z.r): z.zone_type for z in db.query(Zone).all()}

    possible, reasons = can_deliver(rover, order, zones)
    result = calculate_delivery(rover, order, zones, roll_outcome=False)

    feasible = possible and result.feasible
    return DeliverySimulationResponse(
        success=feasible,
        distance=result.distance,
        battery_needed=result.battery_consumed,
        time_estimate=result.time_hours,
        risk_score=1.0 - result.success_chance,
        path=[h.to_dict() for h in result.path],
        warnings=result.warnings + ([] if possible else reasons),
        failure_reason=result.failure_reason if not feasible else None,
        success_chance=result.success_chance,
    )


@router.post("/delivery/assign", response_model=DeliveryResponse)
def assign_delivery(request: AssignOrderRequest, db: Session = Depends(get_db)):
    rover = db.query(Rover).filter(Rover.id == request.rover_id).first()
    order = db.query(Order).filter(Order.id == request.order_id).first()
    
    if not rover:
        raise HTTPException(status_code=404, detail="Ровер не найден")
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    
    if rover.status != RoverStatus.IDLE:
        raise HTTPException(status_code=400, detail=f"Ровер занят: {rover.status.value}")
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Заказ не доступен: {order.status.value}")
    
    zones = {(z.q, z.r): z.zone_type for z in db.query(Zone).all()}
    possible, reasons = can_deliver(rover, order, zones)
    
    if not possible:
        raise HTTPException(status_code=400, detail="; ".join(reasons))
    
    # Simulate delivery (random outcome)
    result = calculate_delivery(rover, order, zones, roll_outcome=True)

    # Round trip already simulated — rover returns to base
    rover.current_battery -= result.battery_consumed
    rover.current_battery = max(0, rover.current_battery)
    rover.total_distance += result.distance
    rover.position_q = rover.base_q
    rover.position_r = rover.base_r
    rover.current_cargo = 0
    rover.updated_at = datetime.utcnow()

    order.assigned_rover_id = rover.id
    order.assigned_at = datetime.utcnow()

    delivery = Delivery(
        rover_id=rover.id,
        order_id=order.id,
        distance=result.distance,
        battery_consumed=result.battery_consumed,
        success=result.success,
        failure_reason=result.failure_reason,
        credits_earned=result.credits_earned,
        path_taken=[h.to_dict() for h in result.path],
        completed_at=datetime.utcnow(),
    )

    state = db.query(GameState).filter(GameState.id == 1).first()
    if state:
        state.total_deliveries += 1
        if result.success:
            order.status = OrderStatus.DELIVERED
            order.delivered_at = datetime.utcnow()
            rover.deliveries_completed += 1
            rover.status = RoverStatus.IDLE
            state.successful_deliveries += 1
            state.credits += result.credits_earned
            state.base_rating = min(100.0, state.base_rating + 2)
        else:
            order.status = OrderStatus.FAILED
            rover.status = RoverStatus.IDLE
            state.failed_deliveries += 1
            state.base_rating = max(0.0, state.base_rating - 5)
            if state.base_rating <= 0:
                state.is_game_over = True
                state.game_over_reason = "Рейтинг базы упал до 0"

    db.add(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


# ---------- Game State ----------
@router.get("/game/state", response_model=GameStateResponse)
def get_game_state(db: Session = Depends(get_db)):
    state = db.query(GameState).filter(GameState.id == 1).first()
    if not state:
        state = GameState(id=1)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


@router.post("/game/next-day", response_model=NextDayResponse)
def next_day(db: Session = Depends(get_db)):
    state = db.query(GameState).filter(GameState.id == 1).first()
    if not state:
        state = GameState(id=1)
        db.add(state)
        db.commit()
        db.refresh(state)
    
    if state.is_game_over:
        raise HTTPException(status_code=400, detail="Игра уже окончена")
    
    rovers = db.query(Rover).all()
    orders = db.query(Order).all()
    zones = {(z.q, z.r): z.zone_type for z in db.query(Zone).all()}
    
    # Get today's deliveries
    today_deliveries = db.query(Delivery).filter(
        Delivery.started_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).all()
    
    state.current_day += 1
    messages, new_orders, events, zone_updates = next_day_logic(state, rovers, orders, zones, today_deliveries)

    for order in new_orders:
        db.add(order)

    saved_events = []
    for ev in events:
        game_event = GameEvent(**ev)
        db.add(game_event)
        saved_events.append(game_event)

    _persist_zone_updates(db, zone_updates)

    db.commit()
    
    # Refresh to get IDs and timestamps
    for ev in saved_events:
        db.refresh(ev)
    for order in new_orders:
        db.refresh(order)
    
    return NextDayResponse(
        day=state.current_day,
        credits=state.credits,
        base_rating=state.base_rating,
        new_orders=new_orders,
        events=[GameEventResponse.model_validate(e) for e in saved_events],
        rover_updates=rovers,
        is_game_over=state.is_game_over,
        game_over_reason=state.game_over_reason,
        won=state.won
    )


@router.post("/game/reset")
def reset_game(db: Session = Depends(get_db)):
    """Reset game to initial state."""
    db.query(Delivery).delete()
    db.query(Order).delete()
    db.query(GameEvent).delete()
    db.query(Rover).delete()
    db.query(Zone).delete()
    db.query(GameState).delete()
    db.commit()

    seed_initial_data(db)
    return {"message": "Игра сброшена"}


# ---------- Events ----------
@router.get("/events", response_model=List[GameEventResponse])
def get_events(db: Session = Depends(get_db)):
    return db.query(GameEvent).order_by(GameEvent.created_at.desc()).limit(50).all()


# ---------- Stats ----------
@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    state = db.query(GameState).filter(GameState.id == 1).first()
    rovers = db.query(Rover).all()
    deliveries = db.query(Delivery).all()
    orders = db.query(Order).all()
    
    return {
        "game_state": state,
        "rovers_count": len(rovers),
        "active_rovers": len([r for r in rovers if r.status == RoverStatus.IDLE]),
        "total_deliveries": len(deliveries),
        "successful_deliveries": len([d for d in deliveries if d.success]),
        "pending_orders": len([o for o in orders if o.status == OrderStatus.PENDING]),
        "total_credits_earned": sum(d.credits_earned for d in deliveries),
        "total_distance": sum(r.total_distance for r in rovers),
    }