import {ResearchListView} from '@/components/ResearchViews';
export const dynamic = 'force-dynamic';
export default async function Page({searchParams}: {searchParams: Promise<Record<string, string | string[] | undefined>>}) {
  const raw = await searchParams;
  const bundle = typeof raw.bundle === 'string' ? raw.bundle : '';
  return <ResearchListView expectedBundle={bundle}/>;
}
