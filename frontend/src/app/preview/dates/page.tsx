import type {Metadata} from 'next';
import Link from 'next/link';
import DateSelector from '@/components/DateSelector';
import DatedFundList from '@/components/DatedFundList';
import DatedFundDetail from '@/components/DatedFundDetail';
import {DatedShell, DatedStateScreen} from '@/components/DatedResearchViews';
import {isCalendarDate, isInDatedRange} from '@/lib/dated-contract';
import {DATED_COPY as C, PREVIEW_STATES, type PreviewState} from '@/lib/dated-presentation';
import {syntheticBundle, syntheticIndex, SYNTHETIC_DATES} from '@/lib/dated-synthetic';

export const dynamic = 'force-dynamic';
export const metadata: Metadata = {title: 'Tarih görünümü önizlemesi · Fon araştırması', robots: {index: false, follow: false}};
const MISMATCH_MESSAGE = 'Bu bağlantının araştırma paketi, seçilen tarih için kayıtlı paketle aynı değil.';

function StateLinks({current}: {current: PreviewState}) {
  return <nav aria-label={C.previewStates} className="detail-note" style={{display: 'flex', flexWrap: 'wrap', gap: '4px 14px', margin: '0 0 18px'}}>
    <strong style={{width: '100%'}}>{C.previewStates}</strong>
    {PREVIEW_STATES.map(([state, label]) => <Link key={state} href={`/preview/dates?state=${state}`} aria-current={state === current ? 'page' : undefined}
      style={{minHeight: 44, display: 'inline-flex', alignItems: 'center', textDecoration: state === current ? 'underline' : 'none', color: '#1b6559', fontWeight: 600}}>{label}</Link>)}
  </nav>;
}

/** Labelled synthetic scaffold of every dated state for owner layout review. No real data. */
export default async function Preview({searchParams}: {searchParams: Promise<Record<string, string | string[] | undefined>>}) {
  const raw = await searchParams;
  const single = (key: string) => typeof raw[key] === 'string' ? raw[key] as string : '';
  const requested = PREVIEW_STATES.some(([state]) => state === single('state')) ? single('state') as PreviewState : 'ready';
  const rawDate = raw.date === undefined ? null : single('date');
  let state: PreviewState = requested;
  if (rawDate !== null && state === 'ready' && (!isCalendarDate(rawDate) || !isInDatedRange(rawDate))) state = 'invalid-date';
  else if (rawDate !== null && state === 'ready' && !SYNTHETIC_DATES.includes(rawDate as typeof SYNTHETIC_DATES[number])) state = 'unregistered-date';
  const date = state === 'early-date' ? SYNTHETIC_DATES[0]
    : rawDate !== null && SYNTHETIC_DATES.includes(rawDate as typeof SYNTHETIC_DATES[number]) ? rawDate : syntheticIndex.default_date;
  const windowEnd = syntheticIndex.default_date;
  const selector = <DateSelector dates={syntheticIndex.entries.map(entry => entry.date)} selected={date} windowEnd={windowEnd} action="/preview/dates"/>;
  const data = syntheticBundle(date);
  let content;
  if (state === 'index-loading') content = <DatedStateScreen kind="index-loading"/>;
  else if (state === 'index-error') content = <DatedStateScreen kind="index-error" message="Örnek hata: yerel tarih görünümü API’sine ulaşılamıyor." retryHref="/preview/dates?state=index-error"/>;
  else if (state === 'invalid-date') content = <DatedStateScreen kind="invalid-date" message="Tarih geçersiz." selector={selector}/>;
  else if (state === 'unregistered-date') content = <DatedStateScreen kind="unregistered-date" message="Bu tarih kayıtlı değil." selector={selector}/>;
  else if (state === 'bundle-loading') content = <DatedStateScreen kind="bundle-loading" selector={selector}/>;
  else if (state === 'bundle-error') content = <DatedStateScreen kind="bundle-error" message="Örnek hata: araştırma paketinin bütünlüğü doğrulanamadı." selector={selector} retryHref="/preview/dates?state=bundle-error"/>;
  else if (state === 'mismatch') content = <DatedStateScreen kind="mismatch" message={MISMATCH_MESSAGE} selector={selector} registeredHref={`/preview/dates?date=${date}`}/>;
  else if (state === 'detail') {
    const detail = data.detail(single('detail')) ?? data.detail(data.list.funds[0].code)!;
    content = <DatedFundDetail detail={detail} synthetic windowEnd={windowEnd}/>;
  } else content = <DatedFundList list={data.list} summary={data.summary} selector={selector} synthetic windowEnd={windowEnd}/>;
  return <DatedShell synthetic>
    <p className="notice" style={{borderLeftColor: 'var(--gold)'}}><strong>{C.syntheticNotice}</strong> {C.syntheticNoticeDetail}</p>
    <StateLinks current={state}/>
    {content}
  </DatedShell>;
}
