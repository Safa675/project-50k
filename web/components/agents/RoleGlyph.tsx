import type {AgentRole} from '@/lib/agents';
import Mascot from './Mascot';

/** Line glyphs for each team member; the Raportör carries the mascot. */
export default function RoleGlyph({role, size = 20}: {role: AgentRole | 'human'; size?: number}) {
  if (role === 'reporter') return <Mascot size={size + 8}/>;
  const common = {className: 'ag-glyph', viewBox: '0 0 24 24', width: size, height: size, fill: 'none', stroke: 'currentColor',
    strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true, focusable: false};
  switch (role) {
    case 'sentinel': return <svg {...common}><path d="M12 3a9 9 0 1 0 9 9"/><path d="M12 7.5a4.5 4.5 0 1 0 4.5 4.5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><path d="m12 12 6.4-6.4"/></svg>;
    case 'hypothesizer': return <svg {...common}><path d="M9.2 17.5h5.6"/><path d="M10.2 20.5h3.6"/><path d="M12 3.5a5.8 5.8 0 0 0-3.4 10.5c.6.4 1 1.2 1 2v1.5h4.8V16c0-.8.4-1.6 1-2A5.8 5.8 0 0 0 12 3.5Z"/></svg>;
    case 'skeptic': return <svg {...common}><circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17Z" fill="currentColor" stroke="none"/></svg>;
    case 'verifier': return <svg {...common}><path d="M12 3.2 5.2 6v5.2c0 4.3 2.9 8 6.8 9.6 3.9-1.6 6.8-5.3 6.8-9.6V6L12 3.2Z"/><path d="m9 12.2 2.1 2.1 3.9-4"/></svg>;
    default: return <svg {...common}><circle cx="10" cy="8" r="3.6"/><path d="M3.6 19.5c.5-3.2 3.2-5.4 6.4-5.4 1.3 0 2.5.3 3.5.9"/><path d="m14.8 18.2 2 2 4-4"/></svg>;
  }
}
