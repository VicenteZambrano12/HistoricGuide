import { useState, useEffect, useRef, useCallback } from 'react';

export function useGpsSimulation(initialPoint) {
  const [gpsPosition, setGpsPosition] = useState(initialPoint);
  const [isWalking, setIsWalking] = useState(false);
  const [walkProgress, setWalkProgress] = useState(100);
  const animRef = useRef(null);

  const startWalkSimulation = useCallback((fromPoint, toPoint, durationMs = 2200, onNearTarget) => {
    if (animRef.current) cancelAnimationFrame(animRef.current);

    setIsWalking(true);
    setWalkProgress(0);
    const startTime = performance.now();

    const step = (now) => {
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / durationMs);
      const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

      const currentX = fromPoint.mapX + (toPoint.mapX - fromPoint.mapX) * ease;
      const currentY = fromPoint.mapY + (toPoint.mapY - fromPoint.mapY) * ease;
      const currentLat = fromPoint.lat + (toPoint.lat - fromPoint.lat) * ease;
      const currentLng = fromPoint.lng + (toPoint.lng - fromPoint.lng) * ease;

      setGpsPosition({
        mapX: currentX,
        mapY: currentY,
        lat: currentLat,
        lng: currentLng
      });
      setWalkProgress(Math.round(t * 100));

      if (t < 1) {
        animRef.current = requestAnimationFrame(step);
      } else {
        setIsWalking(false);
        setWalkProgress(100);
        if (onNearTarget) onNearTarget();
      }
    };

    animRef.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => {
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);

  return {
    gpsPosition,
    setGpsPosition,
    isWalking,
    walkProgress,
    startWalkSimulation
  };
}
