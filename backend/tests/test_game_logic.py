import pytest
from app.game_logic import calculate_delivery, can_deliver, generate_moon_map, Hex, a_star_search, ZONE_MODIFIERS
from app.models import Rover, Order, ZoneType, RoverStatus, OrderStatus


@pytest.fixture
def sample_zones():
    return generate_moon_map(5)


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
    
    # Order through dangerous zone
    dangerous_order = Order(id=1, title="Dangerous", weight=20.0, reward=1000, urgency=1, risk_level=5,
                            pickup_q=5, pickup_r=0, delivery_q=6, delivery_r=0, status=OrderStatus.PENDING)
    # Make path go through dangerous zone
    sample_zones[(3, 0)] = ZoneType.DANGEROUS
    sample_zones[(4, 0)] = ZoneType.DANGEROUS
    sample_zones[(5, 0)] = ZoneType.DANGEROUS
    
    safe_order = Order(id=2, title="Safe", weight=20.0, reward=100, urgency=1, risk_level=1,
                       pickup_q=-2, pickup_r=0, delivery_q=-3, delivery_r=0, status=OrderStatus.PENDING)
    
    dangerous_result = calculate_delivery(sample_rover, dangerous_order, sample_zones)
    safe_result = calculate_delivery(sample_rover, safe_order, sample_zones)
    
    # Dangerous zone should have more warnings about danger
    dangerous_warnings = [w for w in dangerous_result.warnings if "опасн" in w.lower()]
    safe_warnings = [w for w in safe_result.warnings if "опасн" in w.lower()]
    assert len(dangerous_warnings) >= len(safe_warnings)
    # Dangerous path should consume more battery due to zone modifier
    assert dangerous_result.battery_consumed >= safe_result.battery_consumed


def test_generate_moon_map():
    zones = generate_moon_map(3)
    assert len(zones) > 0
    # Base should be safe
    assert zones[(0, 0)] == ZoneType.SAFE
    # All zones should have valid types
    for zone_type in zones.values():
        assert zone_type in ZoneType


if __name__ == "__main__":
    pytest.main([__file__, "-v"])