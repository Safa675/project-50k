import type {Metadata} from 'next';
import {DatedListView} from '@/components/DatedResearchViews';
export const dynamic = 'force-dynamic';
export const metadata: Metadata = {title: 'Tarih görünümü · Fon araştırması', robots: {index: false, follow: false}};
// Server side only sanitises single-valued parameters; every dated fetch happens in the browser.
export default async function Page({searchParams}: {searchParams: Promise<Record<string, string | string[] | undefined>>}) {
  const raw = await searchParams;
  // Absent date means the index default; a repeated date is invalid, never a guess.
  const date = raw.date === undefined ? null : typeof raw.date === 'string' ? raw.date.slice(0, 32) : '';
  const bundle = typeof raw.bundle === 'string' ? raw.bundle.slice(0, 128) : Array.isArray(raw.bundle) ? 'invalid' : '';
  return <DatedListView date={date} bundle={bundle}/>;
}
