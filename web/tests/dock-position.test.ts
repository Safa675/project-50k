import {describe, expect, it} from 'vitest';
import {clampDock, defaultDock, panelPlacement, restoreDock} from '../components/agents/dock-position';

describe('movable mascot geometry', () => {
  it('starts at the lower right and clamps dragged or saved positions', () => {
    const viewport = {width: 1480, height: 712};
    expect(defaultDock(viewport)).toEqual({x: 1360, y: 592});
    expect(clampDock({x: -100, y: 9999}, viewport)).toEqual({x: 12, y: 604});
    expect(restoreDock('{"x":300,"y":100}', viewport)).toEqual({x: 300, y: 100});
    expect(restoreDock('{"x":"invalid","y":0}', viewport)).toEqual(defaultDock(viewport));
    expect(restoreDock('broken', viewport)).toEqual(defaultDock(viewport));
  });
  it('keeps the larger mobile mascot inside a resized viewport', () => {
    expect(clampDock({x: 1300, y: 700}, {width: 390, height: 844})).toEqual({x: 294, y: 700});
  });
  it('fits the panel to the viewport from either anchor edge', () => {
    for (const anchor of [{x: 12, y: 12}, {x: 1360, y: 592}]) {
      const panel = panelPlacement(anchor, {width: 1480, height: 712});
      expect(panel.left).toBeGreaterThanOrEqual(16);
      expect(panel.left + panel.width).toBeLessThanOrEqual(1464);
      expect(panel.top).toBe(8);
      expect(panel.height).toBe(696);
    }
  });
});
