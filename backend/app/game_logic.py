"""
Game logic for Moon Courier Crisis.
Handles delivery simulation, weight/battery calculations, risk assessment.
"""
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.hex_utils import Hex, a_star_search
from app.models import Delivery, EventType, Order, OrderStatus, Rover, RoverStatus, ZoneType


@dataclass
class DeliveryResult:
    success: bool
    distance: float
    battery_consumed: float
    time_hours: float
    credits_earned: float
    path: list[Hex]
    failure_reason: str | None = None
    warnings: list[str] | None = None
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

FAILURE_REASONS = [
    "Поломка навигации в пыльной буре",
    "Перегрев двигателя под нагрузкой",
    "Повреждение колеса на остром реголите",
    "Сбой связи с базой",
    "Непредвиденное сейсмическое событие",
]

DUST_STORM_SPEED = 0.7      # global speed multiplier during a dust storm
DUST_STORM_SUCCESS_PENALTY = 0.1
ROVER_LOST_CHANCE = 0.25    # chance a failed delivery also loses the rover
BASE_CHARGE_PER_DAY = 30.0
CHARGE_BONUS_CAP = 0.5


def _inc(obj, attr: str, delta: float = 1) -> None:
    """Increment a numeric column that may be None on transient (unsaved) objects."""
    setattr(obj, attr, (getattr(obj, attr) or 0) + delta)


def calculate_delivery(
    rover: Rover,
    order: Order,
    zones: dict[tuple[int, int], ZoneType],
    *,
    roll_outcome: bool = True,
    dust_storm: bool = False,
) -> DeliveryResult:
    """
    Simulate a delivery with all game mechanics:
    - Weight affects battery consumption and speed
    - Battery must be sufficient for round trip
    - Zone risks affect success chance
    - Dust storm slows all rovers and lowers success chance
    - Impossible deliveries detected
    """
    warnings = []
    storm_speed = DUST_STORM_SPEED if dust_storm else 1.0
    if dust_storm:
        warnings.append("Пыльная буря: скорость всех роверов -30%, шанс успеха -10%")
    
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
    
    battery_per_km = 0.0  # Will accumulate per zone
    time_hours = 0.0
    risk_accumulator = 0.0
    
    for i in range(len(full_path) - 1):
        current_hex = full_path[i]
        zone = zones.get((current_hex.q, current_hex.r), ZoneType.SAFE)
        modifiers = ZONE_MODIFIERS[zone]
        
        # Battery per segment
        battery_per_km += modifiers.battery_multiplier * weight_factor / rover.efficiency
        
        # Time per segment (hours)
        time_hours += 1.0 / (rover.speed * modifiers.speed_multiplier * storm_speed)
        
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
    if dust_storm:
        success_chance -= DUST_STORM_SUCCESS_PENALTY
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
        failure_reason = random.choice(FAILURE_REASONS)
        credits = 0.0
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


def can_deliver(rover: Rover, order: Order, zones: dict[tuple[int, int], ZoneType]) -> tuple[bool, list[str]]:
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
        est_battery = 0.0
        for h in full_path[:-1]:
            zone = zones.get((h.q, h.r), ZoneType.SAFE)
            est_battery += ZONE_MODIFIERS[zone].battery_multiplier * weight_factor / rover.efficiency
        
        if rover.current_battery < est_battery * 1.1:
            reasons.append(f"Нужно ~{est_battery * 1.1:.0f}% батареи, есть {rover.current_battery:.0f}%")
    
    return len(reasons) == 0, reasons


def generate_orders(day: int, zones: dict[tuple[int, int], ZoneType], base_pos: Hex,
                    existing_orders: list[Order] | None = None) -> list[Order]:
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

        # Urgent orders must be assigned before the end of the next day
        expires_day = day + 1 if urgency >= 4 else None

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
            created_day=day,
            expires_day=expires_day,
        )
        orders.append(order)
    
    return orders


def generate_random_event(day: int, game_state, rovers: list[Rover]) -> dict | None:
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
    
    data: dict[str, Any] = {}
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


def _make_priority_order(day: int, zones: dict[tuple[int, int], ZoneType]) -> Order | None:
    """Create a double-reward urgent order for the PRIORITY_ORDER event."""
    candidates = [pos for pos, z in zones.items() if z != ZoneType.IMPASSABLE and pos != (0, 0)]
    if len(candidates) < 2:
        return None
    pickup = random.choice(candidates)
    delivery = random.choice(candidates)
    while delivery == pickup:
        delivery = random.choice(candidates)
    weight = round(random.uniform(5, 40), 1)
    dist = Hex(pickup[0], pickup[1]).distance(Hex(delivery[0], delivery[1]))
    reward = round((100 + dist * 30 + weight * 2) * 2.0, 1)
    return Order(
        title=f"ПРИОРИТЕТНЫЙ #{day}-{random.randint(100, 999)}",
        description=f"Срочный груз {weight} кг из сектора {pickup[0]},{pickup[1]} в {delivery[0]},{delivery[1]}",
        weight=weight,
        reward=reward,
        urgency=5,
        risk_level=random.randint(2, 5),
        pickup_q=pickup[0],
        pickup_r=pickup[1],
        delivery_q=delivery[0],
        delivery_r=delivery[1],
        status=OrderStatus.PENDING,
        created_day=day,
        expires_day=day + 1,
    )


def apply_event(
    event: dict, game_state, rovers: list[Rover], zones: dict
) -> tuple[list[str], dict[tuple[int, int], ZoneType], list[Order]]:
    """Apply event effects: mutate game state, rovers and zones.

    Returns log messages, zone updates and newly created orders."""
    messages: list[str] = []
    zone_updates: dict[tuple[int, int], ZoneType] = {}
    new_orders: list[Order] = []
    ev_type = event["event_type"]
    data = event.get("data", {})

    if ev_type == EventType.DUST_STORM:
        game_state.dust_storm_active = True
        messages.append("Пыльная буря: скорость всех роверов -30%, шанс успеха -10% сегодня")

    elif ev_type == EventType.SOLAR_FLARE:
        candidates = [
            pos for pos, z in zones.items()
            if z != ZoneType.IMPASSABLE and pos != (0, 0)
        ]
        if candidates:
            q, r = random.choice(candidates)
            game_state.flare_zone = {"q": q, "r": r, "orig": zones[(q, r)].value}
            zones[(q, r)] = ZoneType.DANGEROUS
            zone_updates[(q, r)] = ZoneType.DANGEROUS
            messages.append(f"Солнечная вспышка: сектор ({q},{r}) нестабилен сегодня — зона стала опасной")
        else:
            messages.append("Солнечная вспышка: навигация нестабильна (свободных секторов нет)")

    elif ev_type == EventType.ROVER_MALFUNCTION:
        rover_id = data.get("rover_id")
        repair_days = data.get("repair_days", 1)
        for r in rovers:
            if r.id == rover_id:
                r.status = RoverStatus.BROKEN
                r.repair_days_left = repair_days
                messages.append(f"Ровер {r.name} сломан, ремонт {repair_days} дн.")
                break

    elif ev_type == EventType.METEORITE_IMPACT:
        safe_zones = [pos for pos, z in zones.items() if z != ZoneType.IMPASSABLE and pos != (0, 0)]
        if safe_zones:
            q, r = random.choice(safe_zones)
            zones[(q, r)] = ZoneType.IMPASSABLE
            zone_updates[(q, r)] = ZoneType.IMPASSABLE
            messages.append(f"Метеорит ударил в сектор ({q},{r}) — зона стала непроходимой")

    elif ev_type == EventType.PRIORITY_ORDER:
        order = _make_priority_order(event.get("day", 1), zones)
        if order:
            new_orders.append(order)
            messages.append(f"Поступил ПРИОРИТЕТНЫЙ заказ {order.title}: двойная награда {order.reward:.0f} ₡!")
        else:
            messages.append("Поступил приоритетный заказ, но нет свободных секторов")

    elif ev_type == EventType.BASE_UPGRADE:
        game_state.charge_bonus = min(CHARGE_BONUS_CAP, (game_state.charge_bonus or 0.0) + 0.1)
        messages.append(
            f"База модернизирована: зарядка теперь +{BASE_CHARGE_PER_DAY * (1 + game_state.charge_bonus):.0f}% в день"
        )

    return messages, zone_updates, new_orders


def resolve_delivery(delivery: Delivery, rover: Rover, order: Order, game_state) -> list[str]:
    """Roll the outcome of an in-transit delivery at the end of the day.

    Success: order delivered, rover idles at base.
    Failure: order failed, rover returns the next day; with a small
    chance the rover is lost forever."""
    messages: list[str] = []
    success = random.random() < (delivery.success_chance or 0.0)

    delivery.resolved = True
    delivery.completed_at = datetime.utcnow()
    rover.current_cargo = 0
    rover.position_q = rover.base_q
    rover.position_r = rover.base_r
    _inc(rover, "total_distance", delivery.distance or 0.0)
    _inc(game_state, "total_deliveries")

    if success:
        credits = order.reward * (1.2 if order.urgency >= 4 else 1.0)
        delivery.success = True
        delivery.credits_earned = credits
        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.utcnow()
        _inc(rover, "deliveries_completed")
        rover.current_battery = max(0.0, (rover.current_battery or 0.0) - (delivery.battery_consumed or 0.0))
        rover.status = RoverStatus.IDLE
        _inc(game_state, "successful_deliveries")
        _inc(game_state, "credits", credits)
        game_state.base_rating = min(100.0, (game_state.base_rating or 0.0) + 2)
        messages.append(f"Доставка «{order.title}» выполнена ровером {rover.name}: +{credits:.0f} ₡")
    else:
        delivery.success = False
        delivery.failure_reason = random.choice(FAILURE_REASONS)
        delivery.credits_earned = 0.0
        order.status = OrderStatus.FAILED
        rover.current_battery = max(0.0, (rover.current_battery or 0.0) - (delivery.battery_consumed or 0.0) * 0.5)
        _inc(game_state, "failed_deliveries")
        game_state.base_rating = max(0.0, (game_state.base_rating or 0.0) - 5)
        if random.random() < ROVER_LOST_CHANCE:
            rover.status = RoverStatus.LOST
            _inc(game_state, "rovers_lost")
            messages.append(f"Доставка «{order.title}» провалена: {delivery.failure_reason}. Ровер {rover.name} ПОТЕРЯН")
        else:
            rover.status = RoverStatus.RETURNING
            messages.append(f"Доставка «{order.title}» провалена: {delivery.failure_reason}. {rover.name} возвращается на базу")

    return messages


def next_day_logic(game_state, rovers: list[Rover], orders: list[Order],
                   zones: dict, active_deliveries: list[Delivery]) -> tuple[list[str], list[Order], list[dict], dict[tuple[int, int], ZoneType]]:
    """Process end of day: resolve deliveries, recharge, repair, expire orders,
    generate new orders and events. The day counter is incremented by the caller."""
    messages: list[str] = []
    zone_updates: dict[tuple[int, int], ZoneType] = {}
    current_day = game_state.current_day

    # 1. Rovers returning from a failed delivery arrive at base
    for rover in rovers:
        if rover.status == RoverStatus.RETURNING:
            rover.status = RoverStatus.IDLE
            messages.append(f"{rover.name} вернулся на базу")

    # 2. Yesterday's solar flare fades: restore the affected zone
    flare = game_state.flare_zone
    if flare:
        pos = (flare["q"], flare["r"])
        if zones.get(pos) == ZoneType.DANGEROUS:
            zones[pos] = ZoneType(flare["orig"])
            zone_updates[pos] = ZoneType(flare["orig"])
        game_state.flare_zone = None
        messages.append("Солнечная вспышка закончилась: навигация восстановлена")

    # 3. Recharge rovers that stayed idle at base (BASE_UPGRADE raises the rate)
    charge_amount = BASE_CHARGE_PER_DAY * (1 + (game_state.charge_bonus or 0.0))
    for rover in rovers:
        if rover.status == RoverStatus.IDLE and rover.position_q == rover.base_q and rover.position_r == rover.base_r:
            old_battery = rover.current_battery or 0.0
            rover.current_battery = min(rover.max_battery or 100.0, old_battery + charge_amount)
            if rover.current_battery > old_battery:
                messages.append(f"{rover.name}: заряжен с {old_battery:.0f}% до {rover.current_battery:.0f}%")

    # 4. Resolve deliveries that were in transit today
    rover_by_id = {r.id: r for r in rovers}
    order_by_id = {o.id: o for o in orders}
    for delivery in active_deliveries:
        if delivery.resolved:
            continue
        d_rover = rover_by_id.get(delivery.rover_id)
        d_order = order_by_id.get(delivery.order_id)
        if d_rover is None or d_order is None or d_rover.status != RoverStatus.DELIVERING:
            continue
        messages.extend(resolve_delivery(delivery, d_rover, d_order, game_state))

    # 5. Repair broken rovers at base, one day at a time
    for rover in rovers:
        at_base = rover.position_q == rover.base_q and rover.position_r == rover.base_r
        if (rover.status == RoverStatus.BROKEN and at_base
                and rover.repair_days_left and rover.repair_days_left > 0):
            rover.repair_days_left -= 1
            if rover.repair_days_left <= 0:
                rover.status = RoverStatus.IDLE
                messages.append(f"{rover.name} отремонтирован на базе")
            else:
                messages.append(f"{rover.name}: ремонт продолжается, осталось {rover.repair_days_left} дн.")

    # 6. Expire urgent orders that were not assigned in time
    for order in orders:
        if (order.status == OrderStatus.PENDING and order.expires_day is not None
                and current_day >= order.expires_day):
            order.status = OrderStatus.EXPIRED
            game_state.base_rating = max(0.0, (game_state.base_rating or 0.0) - 5)
            messages.append(f"Заказ {order.title} просрочен! Рейтинг базы -5")

    # 7. New orders for the new day
    new_orders = generate_orders(current_day, zones, Hex(0, 0), orders)
    orders.extend(new_orders)
    if new_orders:
        messages.append(f"Новые заказы: {len(new_orders)}")

    # 8. Reset one-day weather effects before rolling today's event
    game_state.dust_storm_active = False

    # 9. Random event for the new day
    event_data = generate_random_event(current_day, game_state, rovers)
    events: list[dict] = []
    if event_data:
        events.append(event_data)
        event_messages, event_zone_updates, event_orders = apply_event(event_data, game_state, rovers, zones)
        messages.extend(event_messages)
        zone_updates.update(event_zone_updates)
        if event_orders:
            new_orders.extend(event_orders)
            orders.extend(event_orders)

    # 10. End-game checks
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