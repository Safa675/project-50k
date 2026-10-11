import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {ROLE_META, roleFromSlug} from '@/lib/agents';
import {AgentRolePage} from '@/components/agents/TeamPage';

type Params = {params: Promise<{role: string}>};

export async function generateMetadata({params}: Params): Promise<Metadata> {
  const role = roleFromSlug((await params).role);
  return {title: role ? `${ROLE_META[role].name} · Ajan ekibi · BlackSwan` : 'Ajan ekibi · BlackSwan'};
}

export default async function AgentWorkspaceRoute({params}: Params) {
  const role = roleFromSlug((await params).role);
  if (!role) notFound();
  return <AgentRolePage role={role}/>;
}
