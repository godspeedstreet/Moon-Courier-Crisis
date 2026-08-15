import { describe, it, expect } from 'vitest';
import { hexToPixel, pixelToHex, hexDistance, getNeighbors, type HexCoord } from '../lib/hex';

describe('Hex utilities', () => {
  describe('hexToPixel', () => {
    it('converts origin to (0, 0)', () => {
      const result = hexToPixel({ q: 0, r: 0 });
      expect(result.x).toBeCloseTo(0);
      expect(result.y).toBeCloseTo(0);
    });

    it('converts hex coordinates correctly', () => {
      const result = hexToPixel({ q: 1, r: 0 });
      expect(result.x).toBeGreaterThan(0);
      // For pointy-top hex: x = size * 3/2 * q, y = size * sqrt(3)/2 * q
      // With size=36: x = 54, y = 36 * 0.866 * 1 = 31.176
      expect(result.y).toBeCloseTo(31.1769, 1);
    });
  });

  describe('pixelToHex', () => {
    it('rounds pixel coordinates to nearest hex', () => {
      const hex = { q: 2, r: -1 };
      const pixel = hexToPixel(hex);
      const result = pixelToHex(pixel.x, pixel.y);
      expect(result.q).toBe(hex.q);
      expect(result.r).toBe(hex.r);
    });
  });

  describe('hexDistance', () => {
    it('returns 0 for same hex', () => {
      const a: HexCoord = { q: 0, r: 0 };
      const b: HexCoord = { q: 0, r: 0 };
      expect(hexDistance(a, b)).toBe(0);
    });

    it('calculates correct distance', () => {
      const a: HexCoord = { q: 0, r: 0 };
      const b: HexCoord = { q: 3, r: -1 };
      expect(hexDistance(a, b)).toBe(3);
    });

    it('is symmetric', () => {
      const a: HexCoord = { q: -2, r: 3 };
      const b: HexCoord = { q: 4, r: -1 };
      expect(hexDistance(a, b)).toBe(hexDistance(b, a));
    });
  });

  describe('getNeighbors', () => {
    it('returns 6 neighbors', () => {
      const neighbors = getNeighbors({ q: 0, r: 0 });
      expect(neighbors).toHaveLength(6);
    });

    it('neighbors are at distance 1', () => {
      const center: HexCoord = { q: 0, r: 0 };
      const neighbors = getNeighbors(center);
      neighbors.forEach(n => {
        expect(hexDistance(center, n)).toBe(1);
      });
    });
  });
});