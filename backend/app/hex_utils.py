"""
Hex grid utilities for moon map.
Uses axial coordinates (q, r) for hex grid.
"""
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
import math
import random
from app.models import ZoneType


@dataclass
class Hex:
    q: int
    r: int

    def __hash__(self):
        return hash((self.q, self.r))

    def __eq__(self, other):
        if not isinstance(other, Hex):
            return False
        return self.q == other.q and self.r == other.r

    def neighbors(self) -> List['Hex']:
        directions = [
            Hex(1, 0), Hex(1, -1), Hex(0, -1),
            Hex(-1, 0), Hex(-1, 1), Hex(0, 1)
        ]
        return [Hex(self.q + d.q, self.r + d.r) for d in directions]

    def distance(self, other: 'Hex') -> int:
        """Hex distance in axial coordinates."""
        return (abs(self.q - other.q) + 
                abs(self.q + self.r - other.q - other.r) + 
                abs(self.r - other.r)) // 2

    def __lt__(self, other: 'Hex') -> bool:
        """For heapq comparison - compare by (q, r) tuple."""
        if not isinstance(other, Hex):
            return NotImplemented
        return (self.q, self.r) < (other.q, other.r)

    def to_dict(self) -> Dict[str, int]:
        return {"q": self.q, "r": self.r}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'Hex':
        return cls(data["q"], data["r"])


def hex_to_pixel(hex: Hex, size: float = 40.0) -> Tuple[float, float]:
    """Convert hex axial to pixel coordinates for rendering."""
    x = size * (3.0/2.0 * hex.q)
    y = size * (math.sqrt(3)/2.0 * hex.q + math.sqrt(3) * hex.r)
    return (x, y)


def pixel_to_hex(x: float, y: float, size: float = 40.0) -> Hex:
    """Convert pixel to nearest hex axial coordinates."""
    q = (2.0/3.0 * x) / size
    r = (-1.0/3.0 * x + math.sqrt(3)/3.0 * y) / size
    return hex_round(q, r)


def hex_round(q: float, r: float) -> Hex:
    """Round fractional hex coordinates to nearest hex."""
    s = -q - r
    rq = round(q)
    rr = round(r)
    rs = round(s)

    q_diff = abs(rq - q)
    r_diff = abs(rr - r)
    s_diff = abs(rs - s)

    if q_diff > r_diff and q_diff > s_diff:
        rq = -rr - rs
    elif r_diff > s_diff:
        rr = -rq - rs
    else:
        rs = -rq - rr

    return Hex(rq, rr)


def a_star_search(start: Hex, goal: Hex, zones: Dict[Tuple[int, int], ZoneType], 
                  max_distance: int = 50) -> Optional[List[Hex]]:
    """A* pathfinding on hex grid with zone costs."""
    from heapq import heappush, heappop

    def heuristic(h: Hex) -> float:
        return h.distance(goal) * 1.0

    def zone_cost(h: Hex) -> float:
        zone = zones.get((h.q, h.r))
        if zone == ZoneType.IMPASSABLE:
            return float('inf')
        elif zone == ZoneType.DANGEROUS:
            return 3.0
        elif zone == ZoneType.MODERATE:
            return 1.5
        return 1.0

    open_set = [(heuristic(start), 0, start, [])]
    closed_set: Set[Hex] = set()
    g_scores = {start: 0}

    while open_set:
        _, g, current, path = heappop(open_set)

        if current == goal:
            return path + [current]

        if current in closed_set:
            continue
        closed_set.add(current)

        if g > max_distance * 2:
            continue

        for neighbor in current.neighbors():
            if neighbor in closed_set:
                continue

            cost = zone_cost(neighbor)
            if cost == float('inf'):
                continue

            new_g = g + cost
            if neighbor not in g_scores or new_g < g_scores[neighbor]:
                g_scores[neighbor] = new_g
                f = new_g + heuristic(neighbor)
                heappush(open_set, (f, new_g, neighbor, path + [current]))

    return None


def generate_moon_map(radius: int = 8, base_pos: Hex = Hex(0, 0)) -> Dict[Tuple[int, int], ZoneType]:
    """Generate procedural moon map with zones."""
    zones = {}
    
    for q in range(-radius, radius + 1):
        r1 = max(-radius, -q - radius)
        r2 = min(radius, -q + radius)
        for r in range(r1, r2 + 1):
            hex_pos = Hex(q, r)
            dist = hex_pos.distance(base_pos)
            
            # Base zone is always safe
            if dist == 0:
                zones[(q, r)] = ZoneType.SAFE
                continue
            
            # Procedural generation with noise-like pattern
            seed = q * 1000 + r * 100 + radius * 10
            random.seed(seed)
            
            # Distance-based probability
            if dist <= 2:
                # Near base: mostly safe
                roll = random.random()
                if roll < 0.7:
                    zone = ZoneType.SAFE
                elif roll < 0.95:
                    zone = ZoneType.MODERATE
                else:
                    zone = ZoneType.DANGEROUS
            elif dist <= 4:
                # Mid range: mixed
                roll = random.random()
                if roll < 0.4:
                    zone = ZoneType.SAFE
                elif roll < 0.7:
                    zone = ZoneType.MODERATE
                elif roll < 0.95:
                    zone = ZoneType.DANGEROUS
                else:
                    zone = ZoneType.IMPASSABLE
            else:
                # Far range: dangerous
                roll = random.random()
                if roll < 0.2:
                    zone = ZoneType.SAFE
                elif roll < 0.5:
                    zone = ZoneType.MODERATE
                elif roll < 0.85:
                    zone = ZoneType.DANGEROUS
                else:
                    zone = ZoneType.IMPASSABLE
            
            zones[(q, r)] = zone
    
    # Add some named craters/features
    crater_positions = [
        Hex(-5, 2), Hex(4, -3), Hex(-2, -6), Hex(6, 1), 
        Hex(-7, -1), Hex(3, 5), Hex(-4, -4), Hex(0, -7)
    ]
    crater_names = [
        "Tycho", "Copernicus", "Clavius", "Aristarchus",
        "Plato", "Eratosthenes", "Kepler", "Grimaldi"
    ]
    
    for i, pos in enumerate(crater_positions):
        if (pos.q, pos.r) in zones:
            zones[(pos.q, pos.r)] = ZoneType.DANGEROUS
    
    return zones


ZONE_COLORS = {
    ZoneType.SAFE: "#4ade80",      # green
    ZoneType.MODERATE: "#fbbf24",  # yellow
    ZoneType.DANGEROUS: "#f87171", # red
    ZoneType.IMPASSABLE: "#6b7280", # gray
}

ZONE_LABELS = {
    ZoneType.SAFE: "Безопасная",
    ZoneType.MODERATE: "Умеренная",
    ZoneType.DANGEROUS: "Опасная",
    ZoneType.IMPASSABLE: "Непроходимая",
}