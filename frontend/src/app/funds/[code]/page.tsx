import {ResearchDetailView} from '@/components/ResearchViews';
export const dynamic = 'force-dynamic';
export default async function Page({params, searchParams}: {params: Promise<{code: string}>; searchParams: Promise<Record<string, string | string[] | undefined>>}) {
  const [{code}, raw] = await Promise.all([params, searchParams]);
  const query: Record<string, string> = {};
  for (const key of ['q', 'category', 'finding', 'bundle']) query[key] = typeof raw[key] === 'string' ? raw[key] : '';
  const back = new URLSearchParams();
  for (const key of ['q', 'category', 'finding']) if (query[key]) back.set(key, query[key]);
  if (query.bundle) back.set('bundle', query.bundle);
  return <ResearchDetailView code={code} expectedBundle={query.bundle} backQuery={back.toString()}/>;
}
