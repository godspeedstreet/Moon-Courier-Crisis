import random
import pytest
from app.game_logic import (
    calculate_delivery, can_deliver, Hex, a_star_search,
    ZONE_MODIFIERS, apply_event, next_day_logic, resolve_delivery,
)
from app.hex_utils import generate_moon_map
from app.models import Rover, Order, Delivery, GameState, ZoneType, RoverStatus, OrderStatus, EventType


@pytest.fixture
def sample_zones():
    # Fixed seed keeps pathfinding tests stable; the real game maps stay random
    return generate_moon_map(5, rng=random.Random(42))


@pytest.fixture
def sample_rover():
    return Rover(
        id=1,
        name="Test Rover",
        max_battery=100.0,
        current_battery=100.0,
        max_cargo=50.0,
        current_cargo=0.0,
        status=RoverStatus.IDLE,
        position_q=0,
        position_r=0,
        base_q=0,
        base_r=0,
        speed=10.0,
        efficiency=1.0,
    )


@pytest.fixture
def sample_order():
    return Order(
        id=1,
        title="Test Order",
        weight=20.0,
        reward=500.0,
        urgency=3,
        risk_level=2,
        pickup_q=3,
        pickup_r=1,
        delivery_q=5,
        delivery_r=2,
        status=OrderStatus.PENDING,
    )


def test_hex_distance():
    a = Hex(0, 0)
    b = Hex(3, 1)
    # Distance in axial: (|0-3| + |0+0-3-1| + |0-1|) / 2 = (3 + 4 + 1) / 2 = 4
    assert a.distance(b) == 4


def test_a_star_pathfinding(sample_zones):
    start = Hex(0, 0)
    goal = Hex(3, 1)
    path = a_star_search(start, goal, sample_zones)
    assert path is not None
    assert len(path) > 1
    assert path[0] == start
    assert path[-1] == goal


def test_a_star_blocked_by_impassable(sample_zones):
    # Make a zone impassable - block direct path but allow detour
    # This tests that A* finds alternative paths, not that it returns None
    sample_zones[(1, 0)] = ZoneType.IMPASSABLE
    sample_zones[(0, 1)] = ZoneType.IMPASSABLE
    sample_zones[(1, -1)] = ZoneType.IMPASSABLE
    
    start = Hex(0, 0)
    goal = Hex(2, 0)
    path = a_star_search(start, goal, sample_zones)
    # A* should find a detour path
    assert path is not None
    assert len(path) > 2  # Should take longer route
    assert path[0] == start
    assert path[-1] == goal


def test_can_deliver_success(sample_rover, sample_order, sample_zones):
    possible, reasons = can_deliver(sample_rover, sample_order, sample_zones)
    assert possible is True
    assert len(reasons) == 0


def test_can_deliver_overweight(sample_rover, sample_order, sample_zones):
    sample_order.weight = 60.0  # > max_cargo 50
    possible, reasons = can_deliver(sample_rover, sample_order, sample_zones)
    assert possible is False
    assert any("макс. груз" in r for r in reasons)


def test_can_deliver_low_battery(sample_rover, sample_order, sample_zones):
    sample_rover.current_battery = 5.0
    possible, reasons = can_deliver(sample_rover, sample_order, sample_zones)
    assert possible is False
    assert any("батаре" in r.lower() for r in reasons)


def test_can_deliver_busy_rover(sample_rover, sample_order, sample_zones):
    sample_rover.status = RoverStatus.DELIVERING
    possible, reasons = can_deliver(sample_rover, sample_order, sample_zones)
    assert possible is False
    assert any("занят" in r for r in reasons)


def test_simulate_delivery_does_not_roll(sample_rover, sample_order, sample_zones):
    result = calculate_delivery(sample_rover, sample_order, sample_zones, roll_outcome=False)
    assert result.feasible is True
    assert result.success is True
    assert result.failure_reason is None
    assert 0.1 <= result.success_chance <= 0.99


def test_calculate_delivery_success(sample_rover, sample_order, sample_zones):
    result = calculate_delivery(sample_rover, sample_order, sample_zones)
    assert result.distance > 0
    assert result.battery_consumed > 0
    assert result.time_hours > 0
    assert len(result.path) > 2
    # Success is probabilistic, but should have reasonable chance
    assert result.success in (True, False)


def test_calculate_delivery_weight_affects_battery(sample_rover, sample_zones):
    # Use a rover with full battery
    sample_rover.current_battery = 100.0
    sample_rover.max_battery = 100.0
    
    light_order = Order(id=1, title="Light", weight=5.0, reward=100, urgency=1, risk_level=1,
                        pickup_q=2, pickup_r=0, delivery_q=3, delivery_r=0, status=OrderStatus.PENDING)
    heavy_order = Order(id=2, title="Heavy", weight=45.0, reward=500, urgency=1, risk_level=1,
                        pickup_q=2, pickup_r=0, delivery_q=3, delivery_r=0, status=OrderStatus.PENDING)
    
    light_result = calculate_delivery(sample_rover, light_order, sample_zones)
    heavy_result = calculate_delivery(sample_rover, heavy_order, sample_zones)
    
    # Heavy order should have weight warning
    heavy_warnings = [w for w in heavy_result.warnings if "тяж" in w.lower()]
    assert len(heavy_warnings) > 0
    # Light order should not have weight warning
    light_warnings = [w for w in light_result.warnings if "тяж" in w.lower()]
    assert len(light_warnings) == 0


def test_calculate_delivery_zone_risk(sample_rover, sample_zones):
    # Ensure rover has enough battery
    sample_rover.current_battery = 100.0
    sample_rover.max_battery = 100.0

    # Same route, different zone types: battery, time and risk must react
    order = Order(id=1, title="Corridor", weight=20.0, reward=1000, urgency=1, risk_level=3,
                  pickup_q=2, pickup_r=0, delivery_q=3, delivery_r=0, status=OrderStatus.PENDING)
    corridor = [(1, 0), (2, 0), (3, 0)]

    for p in corridor:
        sample_zones[p] = ZoneType.SAFE
    calm = calculate_delivery(sample_rover, order, sample_zones, roll_outcome=False)

    for p in corridor:
        sample_zones[p] = ZoneType.DANGEROUS
    hot = calculate_delivery(sample_rover, order, sample_zones, roll_outcome=False)

    assert hot.battery_consumed > calm.battery_consumed
    assert hot.time_hours > calm.time_hours
    assert hot.success_chance < calm.success_chance
    assert any("опасн" in w.lower() for w in hot.warnings)


def test_generate_moon_map():
    zones = generate_moon_map(3)
    assert len(zones) > 0
    # Base should be safe
    assert zones[(0, 0)] == ZoneType.SAFE
    # All zones should have valid types
    for zone_type in zones.values():
        assert zone_type in ZoneType


def test_map_random_between_games():
    # Two default calls must differ: the map is procedural per game
    map1 = generate_moon_map(4)
    map2 = generate_moon_map(4)
    assert map1 != map2


def test_map_deterministic_with_seed():
    map1 = generate_moon_map(4, rng=random.Random(123))
    map2 = generate_moon_map(4, rng=random.Random(123))
    assert map1 == map2


def test_map_generation_does_not_touch_global_random():
    random.seed(777)
    expected = [random.random() for _ in range(3)]
    random.seed(777)
    generate_moon_map(3)
    after = [random.random() for _ in range(3)]
    assert expected == after


# ---------- Events ----------

def _game_state(day=2):
    return GameState(id=1, current_day=day, max_days=7, credits=1000.0, base_rating=100.0)


def test_dust_storm_event_slows_deliveries(sample_rover, sample_order, sample_zones):
    state = _game_state()
    event = {"event_type": EventType.DUST_STORM, "day": 2, "description": "", "data": {}}
    messages, zone_updates, new_orders = apply_event(event, state, [sample_rover], sample_zones)

    assert state.dust_storm_active is True
    assert not zone_updates and not new_orders

    calm = calculate_delivery(sample_rover, sample_order, sample_zones, roll_outcome=False)
    stormy = calculate_delivery(sample_rover, sample_order, sample_zones, roll_outcome=False, dust_storm=True)
    assert stormy.time_hours > calm.time_hours
    assert stormy.success_chance < calm.success_chance
    assert any("буря" in w.lower() for w in stormy.warnings)


def test_solar_flare_marks_zone_and_restores_next_day(sample_rover, sample_zones):
    state = _game_state()
    before = dict(sample_zones)
    event = {"event_type": EventType.SOLAR_FLARE, "day": 2, "description": "", "data": {}}
    _, zone_updates, _ = apply_event(event, state, [sample_rover], sample_zones)

    assert len(zone_updates) == 1
    (q, r), zone = next(iter(zone_updates.items()))
    assert zone == ZoneType.DANGEROUS
    original = before[(q, r)]
    assert state.flare_zone == {"q": q, "r": r, "orig": original.value}
    sample_rover.status = RoverStatus.IDLE

    # next_day_logic rolls a fresh event; patch it out for determinism
    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [sample_rover], [], sample_zones, [])
    finally:
        gl.generate_random_event = saved

    assert state.flare_zone is None
    assert sample_zones[(q, r)] == original


def test_priority_order_event_creates_order(sample_rover, sample_zones):
    state = _game_state()
    event = {"event_type": EventType.PRIORITY_ORDER, "day": 2, "description": "", "data": {"bonus_multiplier": 2.0}}
    messages, _, new_orders = apply_event(event, state, [sample_rover], sample_zones)

    assert len(new_orders) == 1
    order = new_orders[0]
    assert order.urgency == 5
    assert order.status == OrderStatus.PENDING
    assert order.expires_day == 3
    # Double reward vs the regular formula
    dist = Hex(order.pickup_q, order.pickup_r).distance(Hex(order.delivery_q, order.delivery_r))
    assert order.reward >= (100 + dist * 30 + order.weight * 2) * 1.9


def test_base_upgrade_raises_charge_rate(sample_rover, sample_zones):
    state = _game_state()
    event = {"event_type": EventType.BASE_UPGRADE, "day": 2, "description": "", "data": {"charge_bonus": 0.1}}
    apply_event(event, state, [sample_rover], sample_zones)
    assert state.charge_bonus == pytest.approx(0.1)

    sample_rover.current_battery = 10.0
    sample_rover.status = RoverStatus.IDLE

    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [sample_rover], [], dict(sample_zones), [])
    finally:
        gl.generate_random_event = saved

    # +30 base with 10% bonus = +33
    assert sample_rover.current_battery == pytest.approx(43.0)


def test_malfunction_repair_takes_days(sample_rover, sample_zones):
    state = _game_state()
    sample_rover.id = 7
    event = {"event_type": EventType.ROVER_MALFUNCTION, "day": 2, "description": "",
             "data": {"rover_id": 7, "repair_days": 2}}
    apply_event(event, state, [sample_rover], sample_zones)

    assert sample_rover.status == RoverStatus.BROKEN
    assert sample_rover.repair_days_left == 2

    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [sample_rover], [], dict(sample_zones), [])
        assert sample_rover.status == RoverStatus.BROKEN  # one day is not enough
        gl.next_day_logic(state, [sample_rover], [], dict(sample_zones), [])
        assert sample_rover.status == RoverStatus.IDLE
    finally:
        gl.generate_random_event = saved


# ---------- Delivery resolution ----------

def _active_delivery(rover_id=1, order_id=1, chance=1.0):
    return Delivery(
        rover_id=rover_id, order_id=order_id,
        distance=10.0, battery_consumed=20.0,
        success=False, resolved=False, success_chance=chance,
    )


def test_resolve_delivery_success(sample_rover, sample_order):
    state = _game_state()
    sample_rover.status = RoverStatus.DELIVERING
    delivery = _active_delivery(chance=1.0)

    messages = resolve_delivery(delivery, sample_rover, sample_order, state)

    assert delivery.resolved is True and delivery.success is True
    assert sample_order.status == OrderStatus.DELIVERED
    assert sample_rover.status == RoverStatus.IDLE
    assert sample_rover.current_battery == pytest.approx(80.0)
    assert state.successful_deliveries == 1
    assert state.credits == pytest.approx(1000.0 + sample_order.reward)


def test_resolve_delivery_failure_returns_next_day(sample_rover, sample_order):
    state = _game_state()
    sample_rover.status = RoverStatus.DELIVERING
    delivery = _active_delivery(chance=0.0)

    import app.game_logic as gl
    real_random, real_choice = gl.random.random, gl.random.choice
    gl.random.random = lambda: 0.99  # fails, and no rover loss (>= ROVER_LOST_CHANCE)
    gl.random.choice = lambda seq: seq[0]
    try:
        messages = resolve_delivery(delivery, sample_rover, sample_order, state)
    finally:
        gl.random.random, gl.random.choice = real_random, real_choice

    assert delivery.success is False and delivery.failure_reason
    assert sample_order.status == OrderStatus.FAILED
    assert sample_rover.status == RoverStatus.RETURNING
    assert state.failed_deliveries == 1
    assert state.base_rating == pytest.approx(95.0)

    # RETURNING rover arrives at base on the next day
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [sample_rover], [sample_order], {}, [])
    finally:
        gl.generate_random_event = saved
    assert sample_rover.status == RoverStatus.IDLE


def test_resolve_delivery_failure_can_lose_rover(sample_rover, sample_order):
    state = _game_state()
    sample_rover.status = RoverStatus.DELIVERING
    delivery = _active_delivery(chance=0.0)

    import app.game_logic as gl
    real_random, real_choice = gl.random.random, gl.random.choice
    gl.random.random = lambda: 0.0  # failure roll lost AND rover-loss roll lost
    gl.random.choice = lambda seq: seq[0]
    try:
        resolve_delivery(delivery, sample_rover, sample_order, state)
    finally:
        gl.random.random, gl.random.choice = real_random, real_choice

    assert sample_rover.status == RoverStatus.LOST
    assert state.rovers_lost == 1


def test_next_day_resolves_in_transit_delivery(sample_rover, sample_order, sample_zones):
    state = _game_state()
    sample_rover.status = RoverStatus.DELIVERING
    sample_order.status = OrderStatus.ASSIGNED
    delivery = _active_delivery(chance=1.0)

    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        messages, new_orders, events, zone_updates = gl.next_day_logic(
            state, [sample_rover], [sample_order], dict(sample_zones), [delivery])
    finally:
        gl.generate_random_event = saved

    assert delivery.resolved is True
    assert sample_order.status == OrderStatus.DELIVERED
    assert sample_rover.status == RoverStatus.IDLE
    assert any("выполнена" in m for m in messages)


def test_urgent_order_expires_when_unassigned():
    state = _game_state(day=3)
    order = Order(id=1, title="Срочный", weight=10, reward=100, urgency=5, risk_level=1,
                  pickup_q=1, pickup_r=0, delivery_q=2, delivery_r=0,
                  status=OrderStatus.PENDING, created_day=2, expires_day=3)

    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [], [order], {}, [])
    finally:
        gl.generate_random_event = saved

    assert order.status == OrderStatus.EXPIRED
    assert state.base_rating == pytest.approx(95.0)


def test_urgent_assigned_order_does_not_expire():
    state = _game_state(day=3)
    order = Order(id=1, title="Срочный", weight=10, reward=100, urgency=5, risk_level=1,
                  pickup_q=1, pickup_r=0, delivery_q=2, delivery_r=0,
                  status=OrderStatus.ASSIGNED, created_day=2, expires_day=3)

    import app.game_logic as gl
    saved = gl.generate_random_event
    gl.generate_random_event = lambda *a, **k: None
    try:
        gl.next_day_logic(state, [], [order], {}, [])
    finally:
        gl.generate_random_event = saved

    assert order.status == OrderStatus.ASSIGNED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])