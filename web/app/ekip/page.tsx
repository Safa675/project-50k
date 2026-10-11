import type {Metadata} from 'next';
import {requireUser} from '@/lib/auth';
import {TeamOverviewPage} from '@/components/agents/TeamPage';

export const metadata: Metadata = {title: 'Ajan ekibi · BlackSwan'};

export default async function TeamOverview() {
  const user = await requireUser();
  return <TeamOverviewPage userId={user.user_id} reviewHref={user.role === 'viewer' ? '/method#evidence' : '/review'}
    scopeKey={user.analysis_context?.scope_key}/>;
}
