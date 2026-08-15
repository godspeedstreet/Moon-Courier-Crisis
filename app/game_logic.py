"""
Game logic for Moon Courier Crisis.
Handles delivery simulation, weight/battery calculations, risk assessment.
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import random
import math
from app.models import Rover, Order, ZoneType, RoverStatus, OrderStatus, EventType
from app.hex_utils import Hex, a_star_search, generate_moon_map


@dataclass
class DeliveryResult:
    success: bool
    distance: float
    battery_consumed: float
    time_hours: float
    credits_earned: float
    path: List[Hex]
    failure_reason: Optional[str] = None
    warnings: List[str] = None
    feasible: bool = True
    success_chance: float = 0.95

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class ZoneModifiers:
    risk_multiplier: float
    speed_multiplier: float
    battery_multiplier: float


ZONE_MODIFIERS = {
    ZoneType.SAFE: ZoneModifiers(1.0, 1.0, 1.0),
    ZoneType.MODERATE: ZoneModifiers(1.5, 0.9, 1.2),
    ZoneType.DANGEROUS: ZoneModifiers(3.0, 0.7, 1.5),
    ZoneType.IMPASSABLE: ZoneModifiers(999999.0, 0.0, 999999.0),
}


def calculate_delivery(
    rover: Rover,
    order: Order,
    zones: Dict[Tuple[int, int], ZoneType],
    *,
    roll_outcome: bool = True,
) -> DeliveryResult:
    """
    Simulate a delivery with all game mechanics:
    - Weight affects battery consumption and speed
    - Battery must be sufficient for round trip
    - Zone risks affect success chance
    - Impossible deliveries detected
    """
    warnings = []
    
    # Check cargo capacity
    if order.weight > rover.max_cargo:
        return DeliveryResult(
            success=False,
            distance=0,
            battery_consumed=0,
            time_hours=0,
            credits_earned=0,
            path=[],
            failure_reason=f"Заказ слишком тяжелый: {order.weight} кг > грузоподъёмность {rover.max_cargo} кг",
            warnings=["Превышена грузоподъёмность ровера"],
            feasible=False,
            success_chance=0.0,
        )
    
    # Check if rover is available
    if rover.status != RoverStatus.IDLE:
        return DeliveryResult(
            success=False,
            distance=0,
            battery_consumed=0,
            time_hours=0,
            credits_earned=0,
            path=[],
            failure_reason=f"Ровер занят: {rover.status.value}",
            warnings=[f"Статус ровера: {rover.status.value}"],
            feasible=False,
            success_chance=0.0,
        )
    
    # Pathfinding: base -> pickup -> delivery -> base
    base_pos = Hex(rover.base_q, rover.base_r)
    pickup_pos = Hex(order.pickup_q, order.pickup_r)
    delivery_pos = Hex(order.delivery_q, order.delivery_r)
    
    # Find path segments
    path1 = a_star_search(base_pos, pickup_pos, zones)
    path2 = a_star_search(pickup_pos, delivery_pos, zones)
    path3 = a_star_search(delivery_pos, base_pos, zones)
    
    if not path1 or not path2 or not path3:
        return DeliveryResult(
            success=False,
            distance=0,
            battery_consumed=0,
            time_hours=0,
            credits_earned=0,
            path=[],
            failure_reason="Нет доступного пути (непроходимые зоны)",
            warnings=["Маршрут заблокирован непроходимыми зонами"],
            feasible=False,
            success_chance=0.0,
        )
    
    # Combine paths (avoid duplicating connection points)
    full_path = path1[:-1] + path2[:-1] + path3
    
    # Calculate distance (each hex = ~1 km on moon)
    total_distance = len(full_path) - 1  # hexes between positions
    
    # Calculate battery consumption
    # Base consumption: 1% per km * weight factor * zone factors
    weight_factor = 1.0 + (order.weight / rover.max_cargo) * 0.5  # up to 1.5x at max load
    
    battery_per_km = 0  # Will accumulate per zone
    time_hours = 0
    risk_accumulator = 0
    
    for i in range(len(full_path) - 1):
        current_hex = full_path[i]
        next_hex = full_path[i + 1]
        zone = zones.get((current_hex.q, current_hex.r), ZoneType.SAFE)
        modifiers = ZONE_MODIFIERS[zone]
        
        # Battery per segment
        battery_per_km += modifiers.battery_multiplier * weight_factor / rover.efficiency
        
        # Time per segment (hours)
        time_hours += 1.0 / (rover.speed * modifiers.speed_multiplier)
        
        # Risk accumulation
        risk_accumulator += modifiers.risk_multiplier * (order.risk_level / 5.0)
    
    total_battery_needed = battery_per_km
    
    # Check battery (need enough for round trip + 10% margin)
    battery_margin = 1.1
    if rover.current_battery < total_battery_needed * battery_margin:
        return DeliveryResult(
            success=False,
            distance=total_distance,
            battery_consumed=0,
            time_hours=time_hours,
            credits_earned=0,
            path=full_path,
            failure_reason=f"Недостаточно батареи: нужно {total_battery_needed * battery_margin:.1f}%, есть {rover.current_battery:.1f}%",
            warnings=[f"Требуется заряд: {total_battery_needed * battery_margin:.1f}%"],
            feasible=False,
            success_chance=0.0,
        )
    
    # Add weight warning
    if order.weight > rover.max_cargo * 0.8:
        warnings.append(f"Тяжёлый груз ({order.weight} кг) — повышенный расход батареи")
    
    # Add zone warnings
    dangerous_count = sum(1 for h in full_path if zones.get((h.q, h.r)) == ZoneType.DANGEROUS)
    if dangerous_count > 0:
        warnings.append(f"Маршрут проходит через {dangerous_count} опасных зон")
    
    # Calculate success probability
    base_success = 0.95
    risk_penalty = min(risk_accumulator * 0.02, 0.4)  # max 40% penalty
    weight_penalty = (order.weight / rover.max_cargo) * 0.1  # max 10% at max load
    battery_penalty = max(0, (1.0 - rover.current_battery / rover.max_battery) * 0.15)
    
    success_chance = base_success - risk_penalty - weight_penalty - battery_penalty
    success_chance = max(0.1, min(0.99, success_chance))  # clamp 10%-99%

    if not roll_outcome:
        return DeliveryResult(
            success=True,
            distance=total_distance,
            battery_consumed=total_battery_needed,
            time_hours=time_hours,
            credits_earned=order.reward * (1.2 if order.urgency >= 4 else 1.0),
            path=full_path,
            failure_reason=None,
            warnings=warnings,
            feasible=True,
            success_chance=success_chance,
        )

    # Roll for success
    success = random.random() < success_chance

    if not success:
        failure_reasons = [
            "Поломка навигации в пыльной буре",
            "Перегрев двигателя под нагрузкой",
            "Повреждение колеса на острых реголите",
            "Сбой связи с базой",
            "Непредвиденное сеисмическое событие"
        ]
        failure_reason = random.choice(failure_reasons)
        credits = 0
    else:
        failure_reason = None
        # Credits: base reward minus penalties
        credits = order.reward
        if order.urgency >= 4:
            credits *= 1.2  # urgent bonus
    
    return DeliveryResult(
        success=success,
        distance=total_distance,
        battery_consumed=total_battery_needed if success else total_battery_needed * 0.5,
        time_hours=time_hours,
        credits_earned=credits,
        path=full_path,
        failure_reason=failure_reason,
        warnings=warnings,
        feasible=True,
        success_chance=success_chance,
    )


def can_deliver(rover: Rover, order: Order, zones: Dict[Tuple[int, int], ZoneType]) -> Tuple[bool, List[str]]:
    """Quick check if delivery is possible without full simulation."""
    reasons = []
    
    if order.weight > rover.max_cargo:
        reasons.append(f"Вес {order.weight} кг > макс. груз {rover.max_cargo} кг")
    
    if rover.status != RoverStatus.IDLE:
        reasons.append(f"Ровер занят: {rover.status.value}")
    
    base_pos = Hex(rover.base_q, rover.base_r)
    pickup_pos = Hex(order.pickup_q, order.pickup_r)
    delivery_pos = Hex(order.delivery_q, order.delivery_r)
    
    if not a_star_search(base_pos, pickup_pos, zones):
        reasons.append("Нет пути к точке забора")
    if not a_star_search(pickup_pos, delivery_pos, zones):
        reasons.append("Нет пути к точке доставки")
    if not a_star_search(delivery_pos, base_pos, zones):
        reasons.append("Нет пути обратно на базу")
    
    # Quick battery check
    if reasons:
        return False, reasons
    
    # Estimate battery need
    path1 = a_star_search(base_pos, pickup_pos, zones)
    path2 = a_star_search(pickup_pos, delivery_pos, zones)
    path3 = a_star_search(delivery_pos, base_pos, zones)
    
    if path1 and path2 and path3:
        full_path = path1[:-1] + path2[:-1] + path3
        weight_factor = 1.0 + (order.weight / rover.max_cargo) * 0.5
        est_battery = 0
        for h in full_path[:-1]:
            zone = zones.get((h.q, h.r), ZoneType.SAFE)
            est_battery += ZONE_MODIFIERS[zone].battery_multiplier * weight_factor / rover.efficiency
        
        if rover.current_battery < est_battery * 1.1:
            reasons.append(f"Нужно ~{est_battery * 1.1:.0f}% батареи, есть {rover.current_battery:.0f}%")
    
    return len(reasons) == 0, reasons


def generate_orders(day: int, zones: Dict[Tuple[int, int], ZoneType], base_pos: Hex, 
                    existing_orders: List[Order] = None) -> List[Order]:
    """Generate new orders for the day."""
    if existing_orders is None:
        existing_orders = []
    
    # Count pending orders
    pending_count = sum(1 for o in existing_orders if o.status in [OrderStatus.PENDING, OrderStatus.ASSIGNED])
    
    # Target 3-5 pending orders
    target = random.randint(3, 5)
    to_generate = max(0, target - pending_count)
    
    orders = []
    cargo_positions = [pos for pos, zone in zones.items() if zone != ZoneType.IMPASSABLE and pos != (base_pos.q, base_pos.r)]
    
    for _ in range(to_generate):
        if len(cargo_positions) < 2:
            break
            
        pickup = random.choice(cargo_positions)
        delivery = random.choice(cargo_positions)
        while delivery == pickup:
            delivery = random.choice(cargo_positions)
        
        # Weight: 5-50 kg
        weight = round(random.uniform(5, 50), 1)
        
        # Distance affects reward
        dist = Hex(pickup[0], pickup[1]).distance(Hex(delivery[0], delivery[1]))
        base_reward = 100 + dist * 30 + weight * 2
        
        # Urgency and risk
        urgency = random.randint(1, 5)
        risk_level = random.randint(1, 5)
        
        # Urgent orders expire
        expires_at = None
        if urgency >= 4:
            expires_at = None  # Will be set by game loop with day offset
        
        order = Order(
            title=f"Доставка #{day}-{random.randint(100, 999)}",
            description=f"{weight} кг груза из сектора {pickup[0]},{pickup[1]} в {delivery[0]},{delivery[1]}",
            weight=weight,
            reward=round(base_reward, 1),
            urgency=urgency,
            risk_level=risk_level,
            pickup_q=pickup[0],
            pickup_r=pickup[1],
            delivery_q=delivery[0],
            delivery_r=delivery[1],
            status=OrderStatus.PENDING,
        )
        orders.append(order)
    
    return orders


def generate_random_event(day: int, game_state, rovers: List[Rover]) -> Optional[dict]:
    """Generate a random event for the day."""
    # Base chance increases with days
    base_chance = 0.15 + day * 0.03
    if random.random() > base_chance:
        return None
    
    event_types = [
        (EventType.DUST_STORM, 0.35, "Пыльная буря снижает видимость и скорость всех роверов на 30%"),
        (EventType.SOLAR_FLARE, 0.2, "Солнечная вспышка временно отключает навигацию в секторе"),
        (EventType.ROVER_MALFUNCTION, 0.25, "Случайный ровер требует ремонта"),
        (EventType.PRIORITY_ORDER, 0.1, "Поступил срочный заказ с высокой наградой"),
        (EventType.METEORITE_IMPACT, 0.05, "Метеоритный дождь создаёт новую непроходимую зону"),
        (EventType.BASE_UPGRADE, 0.05, "База получает улучшение: +10% эффективность зарядки"),
    ]
    
    # Weighted choice
    total = sum(w for _, w, _ in event_types)
    r = random.random() * total
    for ev_type, weight, desc in event_types:
        r -= weight
        if r <= 0:
            selected_type = ev_type
            description = desc
            break
    
    data = {}
    if selected_type == EventType.ROVER_MALFUNCTION and rovers:
        idle_rovers = [r for r in rovers if r.status == RoverStatus.IDLE]
        if idle_rovers:
            target = random.choice(idle_rovers)
            data = {"rover_id": target.id, "repair_days": random.randint(1, 3)}
    elif selected_type == EventType.METEORITE_IMPACT:
        data = {"radius": 1}
    elif selected_type == EventType.PRIORITY_ORDER:
        data = {"bonus_multiplier": 2.0}
    elif selected_type == EventType.BASE_UPGRADE:
        data = {"charge_bonus": 0.1}
    
    return {
        "event_type": selected_type,
        "day": day,
        "description": description,
        "data": data
    }


def apply_event(
    event: dict, game_state, rovers: List[Rover], zones: Dict
) -> Tuple[List[str], Dict[Tuple[int, int], ZoneType]]:
    """Apply event effects and return log messages plus zone updates."""
    messages = []
    zone_updates: Dict[Tuple[int, int], ZoneType] = {}
    ev_type = event["event_type"]
    data = event.get("data", {})

    if ev_type == EventType.DUST_STORM:
        messages.append("Пыльная буря: скорость всех роверов снижена на 30% сегодня")

    elif ev_type == EventType.SOLAR_FLARE:
        messages.append("Солнечная вспышка: навигация нестабильна в случайном секторе")

    elif ev_type == EventType.ROVER_MALFUNCTION:
        rover_id = data.get("rover_id")
        repair_days = data.get("repair_days", 1)
        for r in rovers:
            if r.id == rover_id:
                r.status = RoverStatus.BROKEN
                messages.append(f"Ровер {r.name} сломан, ремонт {repair_days} день(ей)")
                break

    elif ev_type == EventType.METEORITE_IMPACT:
        safe_zones = [pos for pos, z in zones.items() if z != ZoneType.IMPASSABLE]
        if safe_zones:
            q, r = random.choice(safe_zones)
            zones[(q, r)] = ZoneType.IMPASSABLE
            zone_updates[(q, r)] = ZoneType.IMPASSABLE
            messages.append(f"Метеорит ударил в сектор ({q},{r}) — зона стала непроходимой")

    elif ev_type == EventType.PRIORITY_ORDER:
        messages.append("Поступил ПРИОРИТЕТНЫЙ заказ с двойной наградой!")

    elif ev_type == EventType.BASE_UPGRADE:
        messages.append("База модернизирована: эффективность зарядки +10%")

    return messages, zone_updates


def next_day_logic(game_state, rovers: List[Rover], orders: List[Order],
                   zones: Dict, deliveries_today: List) -> Tuple[List[str], List[Order], List[dict], Dict[Tuple[int, int], ZoneType]]:
    """Process end of day: recharge, expire orders, generate new orders/events."""
    messages = []
    zone_updates: Dict[Tuple[int, int], ZoneType] = {}

    for rover in rovers:
        if rover.position_q == rover.base_q and rover.position_r == rover.base_r:
            old_battery = rover.current_battery
            rover.current_battery = min(rover.max_battery, rover.current_battery + 30)
            if rover.current_battery > old_battery:
                messages.append(f"{rover.name}: заряжен с {old_battery:.0f}% до {rover.current_battery:.0f}%")

        if rover.status == RoverStatus.RETURNING:
            rover.position_q = rover.base_q
            rover.position_r = rover.base_r
            rover.status = RoverStatus.IDLE
            rover.current_cargo = 0
            messages.append(f"{rover.name} вернулся на базу")

        if rover.status == RoverStatus.BROKEN and rover.position_q == rover.base_q and rover.position_r == rover.base_r:
            rover.status = RoverStatus.IDLE
            messages.append(f"{rover.name} отремонтирован на базе")

    for order in orders:
        if order.status == OrderStatus.PENDING and order.urgency >= 4:
            if random.random() < 0.5:
                order.status = OrderStatus.EXPIRED
                game_state.base_rating -= 5
                messages.append(f"Заказ {order.title} просрочен! Рейтинг базы -5")

    new_orders = generate_orders(game_state.current_day + 1, zones, Hex(0, 0), orders)
    for order in new_orders:
        orders.append(order)
    if new_orders:
        messages.append(f"Новые заказы: {len(new_orders)}")

    event_data = generate_random_event(game_state.current_day + 1, game_state, rovers)
    events = []
    if event_data:
        events.append(event_data)
        event_messages, event_zone_updates = apply_event(event_data, game_state, rovers, zones)
        messages.extend(event_messages)
        zone_updates.update(event_zone_updates)

    if game_state.base_rating <= 0:
        game_state.is_game_over = True
        game_state.game_over_reason = "Рейтинг базы упал до 0"
        messages.append("ИГРА ОКОНЧЕНА: рейтинг базы критически низок")

    if game_state.current_day >= game_state.max_days:
        game_state.is_game_over = True
        game_state.won = True
        game_state.game_over_reason = f"Успешно завершено {game_state.max_days} дней!"
        messages.append(f"ПОБЕДА: пройдено {game_state.max_days} дней!")

    return messages, new_orders, events, zone_updates