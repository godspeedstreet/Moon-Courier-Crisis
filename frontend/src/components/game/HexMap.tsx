import { useMemo, useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Zone } from '../../types';
import { useGameStore } from '../../store/gameStore';
import { 
  hexToPixel, getHexCorners, getZoneColor, HEX_SIZE
} from '../../lib/hex';
import { Button } from '../ui/Button';
import { Truck, Package, Home, Zap, Settings } from 'lucide-react';

interface HexMapProps {
  width: number;
  height: number;
}

export function HexMap({ width, height }: HexMapProps) {
  const { 
    zones, rovers, orders,
    selectedRoverId, selectedOrderId, hoveredHex,
    mapZoom, setMapZoom,
    setHoveredHex, setSelectedRover, setSelectedOrder,
  } = useGameStore();

  const svgRef = useRef<SVGSVGElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, width, height });

  useEffect(() => {
    if (svgRef.current && zones.length > 0) {
      const baseZone = zones.find(z => z.q === 0 && z.r === 0);
      if (baseZone) {
        const { x, y } = hexToPixel(baseZone);
        setViewBox({
          x: x - width / 2 / mapZoom,
          y: y - height / 2 / mapZoom,
          width: width / mapZoom,
          height: height / mapZoom
        });
      }
    }
  }, [zones, width, height, mapZoom]);

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
    const newZoom = Math.min(Math.max(mapZoom * zoomFactor, 0.3), 3);
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    setViewBox(prev => {
      const newWidth = width / newZoom;
      const newHeight = height / newZoom;
      const x = prev.x + mouseX / prev.width * prev.width - mouseX / width * newWidth;
      const y = prev.y + mouseY / prev.height * prev.height - mouseY / height * newHeight;
      return { x, y, width: newWidth, height: newHeight };
    });
    setMapZoom(newZoom);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = (dragStart.x - e.clientX) / mapZoom;
    const dy = (dragStart.y - e.clientY) / mapZoom;
    setViewBox(prev => ({
      ...prev,
      x: prev.x + dx,
      y: prev.y + dy
    }));
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleHexClick = (zone: Zone) => {
    const roverHere = rovers.find(r => r.position_q === zone.q && r.position_r === zone.r);
    const orderPickupHere = orders.find(o => o.pickup_q === zone.q && o.pickup_r === zone.r && o.status === 'pending');
    const orderDeliveryHere = orders.find(o => o.delivery_q === zone.q && o.delivery_r === zone.r && o.status === 'in_transit');
    
    if (roverHere) {
      setSelectedRover(roverHere.id);
      setSelectedOrder(null);
    } else if (orderPickupHere) {
      setSelectedOrder(orderPickupHere.id);
      setSelectedRover(null);
    } else if (orderDeliveryHere) {
      setSelectedOrder(orderDeliveryHere.id);
      setSelectedRover(null);
    } else {
      setSelectedRover(null);
      setSelectedOrder(null);
    }
  };

  const handleHexHover = (zone: Zone | null) => {
    setHoveredHex(zone ? { q: zone.q, r: zone.r } : null);
  };

  const getRoverAt = (q: number, r: number) => rovers.find(rv => rv.position_q === q && rv.position_r === r);
  const getOrderPickupAt = (q: number, r: number) => orders.find(o => o.pickup_q === q && o.pickup_r === r && o.status === 'pending');
  const getOrderDeliveryAt = (q: number, r: number) => orders.find(o => o.delivery_q === q && o.delivery_r === r && o.status === 'in_transit');
  const isBase = (q: number, r: number) => q === 0 && r === 0;

  const visibleZones = useMemo(() => {
    if (!svgRef.current) return zones;
    const padding = 100 / mapZoom;
    return zones.filter(z => {
      const { x, y } = hexToPixel(z);
      return x >= viewBox.x - padding && x <= viewBox.x + viewBox.width + padding &&
             y >= viewBox.y - padding && y <= viewBox.y + viewBox.height + padding;
    });
  }, [zones, viewBox, mapZoom]);

  const getRoverPos = (rover: { position_q: number; position_r: number }) => hexToPixel({ q: rover.position_q, r: rover.position_r });

  return (
    <div className="relative w-full h-full overflow-hidden bg-moon-950" onWheel={handleWheel}>
      <svg
        ref={svgRef}
        viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.width} ${viewBox.height}`}
        className="w-full h-full cursor-grab"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onMouseEnter={() => handleHexHover(null)}
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="hex-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#000" floodOpacity="0.3" />
          </filter>
        </defs>
        
        <g>
          {visibleZones.map(zone => {
            const { x, y } = hexToPixel(zone);
            const color = getZoneColor(zone.zone_type);
            const isHovered = hoveredHex?.q === zone.q && hoveredHex?.r === zone.r;
            const roverHere = getRoverAt(zone.q, zone.r);
            const orderPickupHere = getOrderPickupAt(zone.q, zone.r);
            const orderDeliveryHere = getOrderDeliveryAt(zone.q, zone.r);
            const base = isBase(zone.q, zone.r);
            const selected = (selectedRoverId && roverHere?.id === selectedRoverId) || 
                            (selectedOrderId && (orderPickupHere?.id === selectedOrderId || orderDeliveryHere?.id === selectedOrderId));
            
            return (
              <g key={`${zone.q}-${zone.r}`}>
                <polygon
                  points={getHexCorners(x, y)}
                  fill={base ? '#1e3a5f' : `${color}20`}
                  stroke={selected ? '#fff' : (isHovered ? color : `${color}80`)}
                  strokeWidth={selected ? 3 : (isHovered ? 2 : 1)}
                  filter={base || isHovered ? 'url(#hex-shadow)' : undefined}
                  onClick={() => handleHexClick(zone)}
                  onMouseEnter={() => handleHexHover(zone)}
                  onMouseLeave={() => handleHexHover(null)}
                  style={{ cursor: 'pointer', transition: 'all 0.2s' }}
                />
                
                {base && (
                  <g>
                    <circle cx={x} cy={y} r={HEX_SIZE * 0.4} fill="#1e3a5f" stroke="#3b82f6" strokeWidth={2} />
                    <Home x={x - 10} y={y - 10} width={20} height={20} fill="#3b82f6" />
                    <text x={x} y={y + 25} textAnchor="middle" fill="#3b82f6" fontSize="11" fontWeight="bold" fontFamily="monospace">
                      БАЗА
                    </text>
                  </g>
                )}
                
                {roverHere && (
                  <motion.g
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    whileHover={{ scale: 1.1 }}
                  >
                    <circle cx={x} cy={y - 8} r={14} fill="#1e293b" stroke={selected ? '#fff' : '#64748b'} strokeWidth={selected ? 2 : 1} filter="url(#hex-shadow)" />
                    <Truck x={x - 10} y={y - 18} width={20} height={20} fill="#3b82f6" />
                    <rect x={x - 16} y={y + 10} width={32} height={4} rx={2} fill="#0f172a" />
                    <rect 
                      x={x - 16} y={y + 10} 
                      width={Math.max(2, 32 * roverHere.current_battery / roverHere.max_battery)} 
                      height={4} rx={2} 
                      fill={roverHere.current_battery > 30 ? '#22c55e' : '#ef4444'} 
                    />
                    {roverHere.current_cargo > 0 && (
                      <motion.div
                        animate={{ y: [-2, 2, -2] }}
                        transition={{ duration: 1, repeat: Infinity }}
                        style={{ position: 'absolute', left: x + 18, top: y - 18 }}
                      >
                        <Package width={12} height={12} fill="#fbbf24" />
                      </motion.div>
                    )}
                  </motion.g>
                )}
                
                {orderPickupHere && (
                  <motion.g
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    whileHover={{ scale: 1.1 }}
                  >
                    <circle cx={x} cy={y + 12} r={12} fill="#1e293b" stroke="#fbbf24" strokeWidth={2} filter="url(#hex-shadow)" />
                    <Package x={x - 8} y={y + 4} width={16} height={16} fill="#fbbf24" />
                    <text x={x} y={y + 32} textAnchor="middle" fill="#fbbf24" fontSize="9" fontFamily="monospace">
                      {orderPickupHere.weight}kg
                    </text>
                  </motion.g>
                )}
                
                {orderDeliveryHere && (
                  <motion.g
                    animate={{ scale: [1, 1.05, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <circle cx={x} cy={y + 12} r={12} fill="#1e293b" stroke="#22c55e" strokeWidth={2} strokeDasharray="4,2" filter="url(#hex-shadow)" />
                    <Package x={x - 8} y={y + 4} width={16} height={16} fill="#22c55e" />
                    <text x={x} y={y + 32} textAnchor="middle" fill="#22c55e" fontSize="9" fontFamily="monospace">
                      🎯
                    </text>
                  </motion.g>
                )}
                
                {(zone.zone_type === 'dangerous' || zone.zone_type === 'impassable') && !base && (
                  <text 
                    x={x} y={y - HEX_SIZE - 5} 
                    textAnchor="middle" 
                    fill={color} 
                    fontSize="8" 
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    {zone.zone_type === 'dangerous' ? '⚠' : '⛔'}
                  </text>
                )}
              </g>
            );
          })}
        </g>
        
        <AnimatePresence>
          {selectedRoverId && (
            <motion.circle
              key={`select-rover-${selectedRoverId}`}
              initial={{ r: 0, opacity: 0 }}
              animate={{ r: HEX_SIZE * 1.3, opacity: 0.3 }}
              exit={{ r: HEX_SIZE * 1.5, opacity: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              cx={rovers.find(r => r.id === selectedRoverId) ? getRoverPos(rovers.find(r => r.id === selectedRoverId)!).x : 0}
              cy={rovers.find(r => r.id === selectedRoverId) ? getRoverPos(rovers.find(r => r.id === selectedRoverId)!).y : 0}
              fill="#3b82f6"
              stroke="#3b82f6"
              strokeWidth={2}
            />
          )}
        </AnimatePresence>
      </svg>
      
      <div className="absolute bottom-4 right-4 flex flex-col gap-2">
        <Button variant="outline" size="icon" onClick={() => setMapZoom(1)} title="Сбросить зум">
          <Settings width={16} height={16} />
        </Button>
        <Button variant="outline" size="icon" onClick={() => setMapZoom(mapZoom * 0.8)} title="Уменьшить">
          <Zap width={16} height={16} className="rotate-45" />
        </Button>
        <Button variant="outline" size="icon" onClick={() => setMapZoom(mapZoom * 1.25)} title="Увеличить">
          <Zap width={16} height={16} />
        </Button>
      </div>
      
      <div className="absolute top-4 left-4 bg-moon-900/90 backdrop-blur-sm border border-moon-700 rounded-lg p-3 text-xs">
        <div className="font-medium text-moon-300 mb-2">Легенда зон</div>
        <div className="flex flex-col gap-1.5">
          {(['safe', 'moderate', 'dangerous', 'impassable'] as const).map(type => (
            <div key={type} className="flex items-center gap-2">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: getZoneColor(type), border: '1px solid', borderColor: getZoneColor(type) + '80' }} />
              <span className="text-moon-400 capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}