export type { HexCoord } from '../types';
import type { HexCoord } from '../types';

export const HEX_SIZE = 36;
export const HEX_WIDTH = Math.sqrt(3) * HEX_SIZE;
export const HEX_HEIGHT = 2 * HEX_SIZE;
export const HEX_HORIZONTAL_SPACING = HEX_WIDTH * 0.75;
export const HEX_VERTICAL_SPACING = HEX_HEIGHT * 0.5;

export function hexToPixel(hex: HexCoord): { x: number; y: number } {
  const x = HEX_SIZE * (3.0 / 2.0 * hex.q);
  const y = HEX_SIZE * (Math.sqrt(3) / 2.0 * hex.q + Math.sqrt(3) * hex.r);
  return { x, y };
}

export function pixelToHex(x: number, y: number): HexCoord {
  const q = (2.0 / 3.0 * x) / HEX_SIZE;
  const r = (-1.0 / 3.0 * x + Math.sqrt(3) / 3.0 * y) / HEX_SIZE;
  return hexRound(q, r);
}

function hexRound(q: number, r: number): HexCoord {
  const s = -q - r;
  let rq = Math.round(q);
  let rr = Math.round(r);
  const rs = Math.round(s);

  const qDiff = Math.abs(rq - q);
  const rDiff = Math.abs(rr - r);
  const sDiff = Math.abs(rs - s);

  if (qDiff > rDiff && qDiff > sDiff) {
    rq = -rr - rs;
  } else if (rDiff > sDiff) {
    rr = -rq - rs;
  }

  return { q: rq, r: rr };
}

export function hexDistance(a: HexCoord, b: HexCoord): number {
  return (Math.abs(a.q - b.q) + Math.abs(a.q + a.r - b.q - b.r) + Math.abs(a.r - b.r)) / 2;
}

export function getHexCorners(centerX: number, centerY: number, size: number = HEX_SIZE): string {
  const corners: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    const x = centerX + size * Math.cos(angle);
    const y = centerY + size * Math.sin(angle);
    corners.push(`${x},${y}`);
  }
  return corners.join(' ');
}

export function getNeighbors(hex: HexCoord): HexCoord[] {
  const directions = [
    { q: 1, r: 0 }, { q: 1, r: -1 }, { q: 0, r: -1 },
    { q: -1, r: 0 }, { q: -1, r: 1 }, { q: 0, r: 1 }
  ];
  return directions.map(d => ({ q: hex.q + d.q, r: hex.r + d.r }));
}

export function getHexesInRange(center: HexCoord, range: number): HexCoord[] {
  const results: HexCoord[] = [];
  for (let q = -range; q <= range; q++) {
    const r1 = Math.max(-range, -q - range);
    const r2 = Math.min(range, -q + range);
    for (let r = r1; r <= r2; r++) {
      results.push({ q: center.q + q, r: center.r + r });
    }
  }
  return results;
}

export function interpolatePath(path: HexCoord[], t: number): HexCoord {
  if (path.length < 2) return path[0] || { q: 0, r: 0 };
  const segmentLength = 1 / (path.length - 1);
  const segmentIndex = Math.min(Math.floor(t / segmentLength), path.length - 2);
  const segmentT = (t - segmentIndex * segmentLength) / segmentLength;
  const a = path[segmentIndex];
  const b = path[segmentIndex + 1];
  return {
    q: a.q + (b.q - a.q) * segmentT,
    r: a.r + (b.r - a.r) * segmentT,
  };
}

export const ZONE_COLORS: Record<string, string> = {
  safe: '#4ade80',
  moderate: '#fbbf24',
  dangerous: '#f87171',
  impassable: '#6b7280',
};

export const ZONE_LABELS: Record<string, string> = {
  safe: 'Безопасная',
  moderate: 'Умеренная',
  dangerous: 'Опасная',
  impassable: 'Непроходимая',
};

export function getZoneColor(zoneType: string): string {
  return ZONE_COLORS[zoneType] || '#6b7280';
}