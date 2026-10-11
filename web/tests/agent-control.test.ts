import {describe, expect, it} from 'vitest';
import {AgentDataError, parseTeam, parseTeamControl} from '../lib/agents';

const changed_at = '2026-10-11T09:00:00Z';
describe('persistent team control contract', () => {
  it('preserves pause while existing work finishes and supports an idle pause', () => {
    expect(parseTeamControl({paused: true, changed_at, running_tasks: 2, finishing: true}).finishing).toBe(true);
    expect(parseTeamControl({paused: true, changed_at, running_tasks: 0, finishing: false}).paused).toBe(true);
    expect(parseTeamControl({paused: false, changed_at, running_tasks: 2, finishing: false}).paused).toBe(false);
  });
  it('rejects malformed or contradictory control states', () => {
    for (const value of [null, {paused: 'false', changed_at, running_tasks: 0, finishing: false},
      {paused: false, changed_at, running_tasks: 1, finishing: true},
      {paused: true, changed_at, running_tasks: -1, finishing: false}]) {
      expect(() => parseTeamControl(value)).toThrow(AgentDataError);
    }
  });
  it('accepts old snapshots without inventing a running state', () => {
    const base = {now: changed_at, agents: [], counts: {}, links: []};
    expect(parseTeam(base).control).toBeNull();
    expect(parseTeam({...base, control: {paused: true, changed_at, running_tasks: 0, finishing: false}}).control?.paused).toBe(true);
  });
});
