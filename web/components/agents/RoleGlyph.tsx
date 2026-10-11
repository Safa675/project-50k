import type {AgentRole} from '@/lib/agents';

const artwork: Record<AgentRole, string> = {
  sentinel: 'nobetci', hypothesizer: 'hipotezci', skeptic: 'supheci', verifier: 'dogrulayici', reporter: 'raportor',
};

/** Each role uses its supplied mascot; the human retains the existing review glyph. */
export default function RoleGlyph({role, size = 20}: {role: AgentRole | 'human'; size?: number}) {
  if (role !== 'human') return <img className="ag-role-art" src={`/agent-logos/blackswan-${artwork[role]}.svg`}
    width={size} height={size} alt="" aria-hidden="true" draggable={false}/>;
  return <svg className="ag-glyph" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor"
    strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    <circle cx="10" cy="8" r="3.6"/><path d="M3.6 19.5c.5-3.2 3.2-5.4 6.4-5.4 1.3 0 2.5.3 3.5.9"/>
    <path d="m14.8 18.2 2 2 4-4"/>
  </svg>;
}
