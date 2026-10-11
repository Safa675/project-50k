export type DockPoint = {x: number; y: number};
export type DockViewport = {width: number; height: number};
export function dockSize(width: number): number {return width < 640 ? 84 : 96;}
const bound = (value: number, maximum: number, margin: number) => Math.max(margin, Math.min(value, Math.max(margin, maximum)));
export function clampDock(point: DockPoint, viewport: DockViewport): DockPoint {
  const size = dockSize(viewport.width), margin = 12;
  return {x: bound(point.x, viewport.width - size - margin, margin), y: bound(point.y, viewport.height - size - margin, margin)};
}
export function defaultDock(viewport: DockViewport): DockPoint {
  const margin = viewport.width < 640 ? 16 : 24, size = dockSize(viewport.width);
  return clampDock({x: viewport.width - size - margin, y: viewport.height - size - margin}, viewport);
}
export function restoreDock(value: string | null, viewport: DockViewport): DockPoint {
  try {
    const point: unknown = value ? JSON.parse(value) : null;
    if (point && typeof point === 'object' && 'x' in point && 'y' in point &&
      typeof point.x === 'number' && Number.isFinite(point.x) && typeof point.y === 'number' && Number.isFinite(point.y)) {
      return clampDock({x: point.x, y: point.y}, viewport);
    }
  } catch {/* Invalid or unavailable storage uses the default position. */}
  return defaultDock(viewport);
}
export function panelPlacement(anchor: DockPoint, viewport: DockViewport) {
  const width = Math.min(1200, viewport.width - 32), height = Math.min(880, viewport.height - 16);
  const preferredTop = anchor.y > viewport.height / 2 ? anchor.y - height - 12 : anchor.y + dockSize(viewport.width) + 12;
  return {left: bound(anchor.x + dockSize(viewport.width) - width, viewport.width - width - 16, 16),
    top: bound(preferredTop, viewport.height - height - 8, 8), width, height, right: 'auto', bottom: 'auto'} as const;
}
