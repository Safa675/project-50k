'use client';
import {useTranslations} from 'next-intl';
import Link from 'next/link';
import {useSearchParams} from 'next/navigation';
import type {Fund, ResearchSummary} from '@/lib/research-contract';
import {matchesFund, percent, screenLabel, flowLabel, assessmentLabel, type FindingFilter} from '@/lib/presentation';
import {DataTable, DataTableHeader, DataTableHeaderCell, DataTableBody, DataTableRow, DataTableCell} from './primitives/DataTable';
import Toolbar from './primitives/Toolbar';
import Stat from './primitives/Stat';
import Chip from './primitives/Chip';
import EmptyState from './primitives/EmptyState';
import {inputClass, selectClass} from './primitives/form';
import Shell from './Shell';

interface Props {
  funds: Fund[];
  summary: ResearchSummary;
  synthetic?: boolean;
  bundleId?: string;
}
type Filters = {query: string; category: string; finding: FindingFilter};
function readFilters(params: Pick<URLSearchParams, 'getAll'>): Filters {
  const single = (key: string) => {
    const values = params.getAll(key);
    return values.length === 1 ? values[0] : '';
  };
  const finding = single('finding');
  return {
    query: single('q'),
    category: single('category'),
    finding: ['all', 'two', 'one', 'unavailable', 'none'].includes(finding) ? finding as FindingFilter : 'all',
  };
}
export default function FundList({funds, summary, synthetic = false, bundleId = 'synthetic'}: Props) {
  const t = useTranslations('app');
  const searchParams = useSearchParams();
  const {query, category, finding} = readFilters(searchParams);
  const categories = [...new Set(funds.flatMap(fund => fund.category ? [fund.category] : []))].sort((a, b) => a.localeCompare(b, 'tr'));
  const filtered = funds.filter(fund => matchesFund(fund, query, category, finding));
  function filters(q: string, c: string, f: FindingFilter) {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (c) params.set('category', c);
    if (f !== 'all') params.set('finding', f);
    if (!synthetic) params.set('bundle', bundleId);
    return params;
  }
  function change(update: Partial<Filters>) {
    // Filter-only history updates avoid delayed RSC responses restoring old controls.
    // Read the latest URL so rapid edits cannot use a stale render's sibling filters.
    const next = {...readFilters(new URLSearchParams(window.location.search)), ...update};
    const params = filters(next.query, next.category, next.finding);
    window.history.replaceState(null, '', `${synthetic ? '/preview' : '/'}${params.size ? '?' + params.toString() : ''}`);
  }
  function href(code: string) {
    const params = filters(query, category, finding);
    if (synthetic) { params.set('detail', code); return `/preview?${params.toString()}`; }
    return `/funds/${code}?${params.toString()}`;
  }
  return <Shell synthetic={synthetic}>
    <section className="page-intro">
      <div>
        <p className="eyebrow">Sabit tarih · {synthetic ? 'Tasarım önizlemesi' : '100 fon'}</p>
        <h1>Fonların verileri ne söylüyor?</h1>
        <p>Benzer fonlara göre getiri farkını ve tahmini para hareketini ayrı ayrı inceleyin. Her yorumun hesabı ve kaynakları fon detayında.</p>
      </div>
      <div className="cutoff"><span>İnceleme zamanı</span>{t('cutoff')}</div>
    </section>
    <div className="notice">
      <strong>{synthetic ? 'Bu ekrandaki fonlar ve sayılar tamamen örnektir.' : 'Bu ekran geçmiş arşiv verilerini inceler.'}</strong>{' '}
      {synthetic ? 'Gerçek fon bulgusu veya ölçülmüş başarı göstermez.' : 'Gerçek zamanda üretilmiş kriz öncesi alarm değildir. Eşik aşımı, dolandırıcılık kanıtı sayılmaz.'}
    </div>
    <div className="stats">
      <Stat label="Listelenen fon" value={summary.total} hint={`${summary.total} / ${synthetic ? summary.total : summary.denominator} seçili fon`}/>
      <Stat label="İki hesap mevcut" value={summary.fully_assessable} hint={`${summary.fully_assessable} / ${summary.total} fon`}/>
      <Stat label="Eksik değerlendirme" value={summary.partially_assessable} hint={`${summary.partially_assessable} / ${summary.total} fon`}/>
      <Stat label="Değerlendirilemiyor" value={summary.unavailable} hint={`${summary.unavailable} / ${summary.total} fon`}/>
    </div>
    <p className="detail-note">Güncel D1 hesabı: {summary.d1_assessable} / {summary.total} fon · Tahmini para hareketi hesabı: {summary.flow_assessable} / {summary.total} fon · Son gözlemi eski D1: {summary.d1_stale} / {summary.total} fon</p>
    <Toolbar
      leading={<label className="w-full min-w-[240px]"><span className="mb-1 block text-xs text-[var(--text-secondary)]">Fon ara</span><input aria-label="Fon ara" className={inputClass} placeholder={t('search')} value={query} onChange={event => change({query: event.target.value})}/></label>}
      trailing={<button className="button" onClick={() => change({query: '', category: '', finding: 'all'})}>Filtreleri temizle</button>}
    >
      <label><span className="mb-1 block text-xs text-[var(--text-secondary)]">Kategori</span><select aria-label="Kategori" className={selectClass} value={category} onChange={event => change({category: event.target.value})}><option value="">{t('allCategories')}</option>{categories.map(value => <option key={value}>{value}</option>)}</select></label>
      <label><span className="mb-1 block text-xs text-[var(--text-secondary)]">Bulgu</span><select aria-label="Bulgu" className={selectClass} value={finding} onChange={event => change({finding: event.target.value as FindingFilter})}><option value="all">{t('allFindings')}</option><option value="two">{t('two')}</option><option value="one">{t('one')}</option><option value="unavailable">{t('unavailable')}</option><option value="none">{t('none')}</option></select></label>
    </Toolbar>
    <div className="results-head"><span aria-live="polite">{filtered.length} / {summary.total} fon gösteriliyor</span><span>Sıra: iki bulgu → tek bulgu → veri yetersiz → eşik aşımı yok</span></div>
    {filtered.length === 0 ? <EmptyState title="Aramanızla eşleşen fon yok" description="Fon kodunu veya filtreleri değiştirin." action={<button className="button" onClick={() => change({query: '', category: '', finding: 'all'})}>Filtreleri temizle</button>}/> : <>
      <div className="desktop-funds">
        <DataTable minWidth={960}>
          <DataTableHeader><tr><DataTableHeaderCell>Fon</DataTableHeaderCell><DataTableHeaderCell>Getiri farkı · D1</DataTableHeaderCell><DataTableHeaderCell>Tahmini para hareketi</DataTableHeaderCell><DataTableHeaderCell>Veriye dayalı yorum</DataTableHeaderCell><DataTableHeaderCell>Veri durumu</DataTableHeaderCell></tr></DataTableHeader>
          <DataTableBody>{filtered.map(fund => <DataTableRow key={fund.code}>
            <DataTableCell><Link href={href(fund.code)} className="fund-code">{fund.code} ↗</Link><div className="fund-name">{fund.name}</div><span className="metric-hint">{fund.category ?? 'Kategori bilinmiyor'}</span></DataTableCell>
            <DataTableCell><span className="metric-value">{percent(fund.d1.statistic)}</span><span className="metric-hint">{screenLabel(fund.d1)}</span></DataTableCell>
            <DataTableCell><span className="metric-value">{percent(fund.flow.statistic)}</span><span className="metric-hint">{flowLabel(fund)}</span></DataTableCell>
            <DataTableCell className="comment-cell">{fund.comment_tr}</DataTableCell>
            <DataTableCell><Chip variant={fund.assessment === 'FULL' ? 'outline' : 'warning'}>{assessmentLabel(fund)}</Chip></DataTableCell>
          </DataTableRow>)}</DataTableBody>
        </DataTable>
      </div>
      <div className="mobile-funds">{filtered.map(fund => <article className="mobile-fund" key={fund.code}>
        <div className="mobile-fund-head"><div><Link href={href(fund.code)} className="fund-code">{fund.code} ↗</Link><div className="fund-name">{fund.name}</div><span className="metric-hint">{fund.category ?? 'Kategori bilinmiyor'}</span></div><Chip variant={fund.assessment === 'FULL' ? 'outline' : 'warning'}>{assessmentLabel(fund)}</Chip></div>
        <p>{fund.comment_tr}</p>
        <div className="mobile-metrics"><div><span className="metric-hint">Getiri farkı · D1</span><span className="metric-value">{percent(fund.d1.statistic)}</span>{screenLabel(fund.d1)}</div><div><span className="metric-hint">Tahmini para hareketi</span><span className="metric-value">{percent(fund.flow.statistic)}</span>{flowLabel(fund)}</div></div>
      </article>)}</div>
    </>}
    <p className="detail-note mt-5">Getiri farkı: son 60 ortak fiyat tarihi. Tahmini para hareketi: Temmuz → Ağustos 2026. İki dönem aynı değildir.</p>
    <details className="detail-note"><summary>Araştırma paketinin sürümü</summary><code className="source-hash">{synthetic ? 'Örnek veri' : bundleId}</code></details>
  </Shell>;
}
