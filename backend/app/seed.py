"""Initial game data seeding."""
from sqlalchemy.orm import Session

from app.hex_utils import generate_moon_map, Hex
from app.game_logic import ZONE_MODIFIERS, generate_orders
from app.models import Zone, Rover, GameState, Order


def seed_initial_data(db: Session) -> None:
    """Populate database with default zones, rovers, game state and starting orders."""
    game_state = GameState(id=1, current_day=1, max_days=7, credits=1000.0, base_rating=100.0)
    db.add(game_state)

    zone_data = generate_moon_map(8)
    for (q, r), zone_type in zone_data.items():
        modifiers = ZONE_MODIFIERS[zone_type]
        db.add(Zone(
            q=q, r=r, zone_type=zone_type,
            risk_modifier=modifiers.risk_multiplier,
            speed_modifier=modifiers.speed_multiplier,
        ))

    for rover in [
        Rover(name="Ровер-Альфа", max_battery=100, max_cargo=50, speed=10, efficiency=1.0),
        Rover(name="Ровер-Бета", max_battery=120, max_cargo=40, speed=12, efficiency=1.1),
        Rover(name="Ровер-Гамма", max_battery=80, max_cargo=70, speed=8, efficiency=0.9),
    ]:
        db.add(rover)

    db.flush()

    initial_orders = generate_orders(1, zone_data, Hex(0, 0), [])
    for order in initial_orders:
        db.add(order)

    db.commit()
