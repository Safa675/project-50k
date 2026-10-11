'use client';

import {useEffect, useRef, useState, type KeyboardEvent, type PointerEvent} from 'react';
import {clampDock, defaultDock, restoreDock, type DockPoint, type DockViewport} from './dock-position';

export default function useDockPosition(viewer: string) {
  const [position, setPosition] = useState<DockPoint | null>(null);
  const [viewport, setViewport] = useState<DockViewport | null>(null);
  const [dragging, setDragging] = useState(false);
  const gesture = useRef<{id: number; x: number; y: number; start: DockPoint; latest: DockPoint; moved: boolean} | null>(null);
  const suppress = useRef(false);
  const storageKey = `blackswan-dock-position:${viewer}`;
  const screen = () => ({width: window.innerWidth, height: window.innerHeight});
  function save(point: DockPoint) {
    setPosition(point);
    try {window.localStorage.setItem(storageKey, JSON.stringify(point));} catch {/* Dragging also works without storage. */}
  }
  useEffect(() => {
    const view = screen();
    let stored: string | null = null;
    try {stored = window.localStorage.getItem(storageKey);} catch {/* Use the default. */}
    setViewport(view); setPosition(restoreDock(stored, view));
    function resize() {const next = screen(); setViewport(next); setPosition(point => point ? clampDock(point, next) : defaultDock(next));}
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [storageKey]);
  function onPointerDown(event: PointerEvent<HTMLButtonElement>) {
    if (event.button !== 0 || !event.isPrimary) return;
    const rect = event.currentTarget.getBoundingClientRect(), start = {x: rect.x, y: rect.y};
    gesture.current = {id: event.pointerId, x: event.clientX, y: event.clientY, start, latest: start, moved: false};
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function onPointerMove(event: PointerEvent<HTMLButtonElement>) {
    const current = gesture.current;
    if (!current || current.id !== event.pointerId) return;
    const dx = event.clientX - current.x, dy = event.clientY - current.y;
    if (!current.moved && Math.hypot(dx, dy) < 6) return;
    current.moved = true;
    current.latest = clampDock({x: current.start.x + dx, y: current.start.y + dy}, screen());
    setDragging(true); setPosition(current.latest); event.preventDefault();
  }
  function onPointerUp(event: PointerEvent<HTMLButtonElement>) {
    const current = gesture.current;
    if (!current || current.id !== event.pointerId) return;
    if (current.moved) {save(current.latest); suppress.current = true; window.setTimeout(() => {suppress.current = false;}, 0);}
    gesture.current = null; setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  function onPointerCancel() {gesture.current = null; setDragging(false); suppress.current = false;}
  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const amount = event.shiftKey ? 40 : 20;
    const moves: Record<string, DockPoint> = {ArrowLeft: {x: -amount, y: 0}, ArrowRight: {x: amount, y: 0},
      ArrowUp: {x: 0, y: -amount}, ArrowDown: {x: 0, y: amount}};
    if (event.key === 'Home') {event.preventDefault(); save(defaultDock(screen()));}
    else if (moves[event.key]) {event.preventDefault(); const point = position ?? defaultDock(screen()), delta = moves[event.key];
      save(clampDock({x: point.x + delta.x, y: point.y + delta.y}, screen()));}
  }
  return {position, viewport, dragging, style: position ? {left: position.x, top: position.y, right: 'auto', bottom: 'auto'} : undefined,
    handlers: {onPointerDown, onPointerMove, onPointerUp, onPointerCancel, onKeyDown},
    consumeDrag: () => {if (!suppress.current) return false; suppress.current = false; return true;}};
}
