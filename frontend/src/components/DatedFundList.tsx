'use client';
import Link from 'next/link';
import {useState, type ReactNode, type Ref} from 'react';
import type {DatedListResponse, DatedRecord, DatedSummaryResponse} from '@/lib/dated-contract';
import {DATED_COPY as C, DATED_EXACT as S, commentWithNote, d1StateLabel, datedDetailHref, fixedViewHref,
  formatCutoff, listHeading, matchesDatedRecord, ofHundred, snapshotSentence} from '@/lib/dated-presentation';
import {percent} from '@/lib/presentation';
import {DataTable, DataTableHeader, DataTableHeaderCell, DataTableBody, DataTableRow, DataTableCell} from './primitives/DataTable';
import Stat from './primitives/Stat';
import Chip from './primitives/Chip';
import EmptyState from './primitives/EmptyState';
import {inputClass} from './primitives/form';

interface Props {
  list: DatedListResponse;
  summary: DatedSummaryResponse;
  synthetic?: boolean;
  selector?: ReactNode;
  headingRef?: Ref<HTMLHeadingElement>;
  windowEnd: string;
}
const variant = (fund: DatedRecord) => fund.d1_state === 'ELIGIBLE_CROSSING' ? 'warning' : fund.d1_state === 'ELIGIBLE_NO_CROSSING' ? 'outline' : 'neutral';
function Comment({fund}: {fund: DatedRecord}) {
  return <>{commentWithNote(fund).map(text => <span key={text} style={{display: 'block'}}>{text}</span>)}</>;
}

/** D1-only list for one sealed date. Every label and denominator comes from this date's response. */
export default function DatedFundList({list, summary, synthetic = false, selector, headingRef, windowEnd}: Props) {
  const [query, setQuery] = useState('');
  const date = list.cutoff_date;
  const counts = summary.summary;
  const filtered = list.funds.filter(fund => matchesDatedRecord(fund, query));
  const href = (code: string) => datedDetailHref(code, date, list.immutable_bundle_id, synthetic);
  return <div data-dated-date={date} data-dated-bundle={list.immutable_bundle_id}>
    <section className="page-intro">
      <div>
        <p className="eyebrow">{synthetic ? C.syntheticEyebrow : C.eyebrow}</p>
        <h1 ref={headingRef} tabIndex={-1}>{listHeading(date)}</h1>
        <p>{C.intro}</p>
      </div>
      <div className="cutoff"><span>{C.cutoffCaption}</span>{formatCutoff(list.cutoff_at)}{date === windowEnd && <small className="detail-note" style={{display: 'block', marginTop: 6}}>{S.windowEnd}</small>}</div>
    </section>
    {selector}
    <div className="notice">
      <strong>{synthetic ? C.syntheticNotice : C.archiveNotice}</strong>{' '}{synthetic ? C.syntheticNoticeDetail : C.archiveNoticeDetail}
      <p style={{margin: '8px 0 0'}}>{S.survivorship}</p>
      <p style={{margin: '8px 0 0'}}>{snapshotSentence(summary.snapshot.latest_retrieved_at)}</p>
    </div>
    <div className="stats">
      <Stat label={C.statCrossing} value={counts.d1_eligible_crossing} hint={ofHundred(counts.d1_eligible_crossing, counts.denominator)}/>
      <Stat label={C.statNoCrossing} value={counts.d1_eligible_no_crossing} hint={ofHundred(counts.d1_eligible_no_crossing, counts.denominator)}/>
      <Stat label={C.statStale} value={counts.d1_stale} hint={ofHundred(counts.d1_stale, counts.denominator)}/>
      <Stat label={C.statUnavailable} value={counts.d1_unavailable} hint={ofHundred(counts.d1_unavailable, counts.denominator)}/>
    </div>
    <p className="detail-note">{C.noPricePrefix}{ofHundred(counts.no_price_at_cutoff, counts.denominator)}{C.noPriceSuffix}</p>
    <div className="notice">
      <strong>{C.notComputedHeading}:</strong> {S.notComputed}{' '}
      <Link href={fixedViewHref(synthetic)} className="source-link" style={{display: 'inline', margin: 0}}>{S.fixedViewLink}</Link>
    </div>
    <div className="flex flex-wrap items-end justify-between gap-3 rounded-[var(--r-lg)] border border-[var(--border-subtle)] bg-[var(--surface-base)] px-4 py-3">
      <label style={{flex: '1 1 240px', maxWidth: 420}}><span className="mb-1 block text-xs text-[var(--text-secondary)]">{C.searchLabel}</span>
        <input aria-label={C.searchLabel} className={inputClass} style={{minHeight: 44}} placeholder={C.searchPlaceholder} value={query} onChange={event => setQuery(event.target.value)}/></label>
      <button type="button" className="button" style={{minHeight: 44}} onClick={() => setQuery('')}>{C.clearSearch}</button>
    </div>
    <div className="results-head"><span aria-live="polite">{filtered.length} / {list.funds.length}{C.shownSuffix}</span><span>{C.order}</span></div>
    {filtered.length === 0 ? <EmptyState title={C.noMatchTitle} description={C.noMatchDescription}/> : <>
      <div className="desktop-funds">
        <DataTable minWidth={960}>
          <DataTableHeader><tr><DataTableHeaderCell>{C.columnFund}</DataTableHeaderCell><DataTableHeaderCell>{C.columnD1}</DataTableHeaderCell><DataTableHeaderCell>{C.columnThreshold}</DataTableHeaderCell><DataTableHeaderCell>{C.columnState}</DataTableHeaderCell><DataTableHeaderCell>{C.columnComment}</DataTableHeaderCell></tr></DataTableHeader>
          <DataTableBody>{filtered.map(fund => <DataTableRow key={fund.code} data-code={fund.code}>
            <DataTableCell><Link href={href(fund.code)} className="fund-code">{fund.code} ↗</Link><div className="fund-name">{fund.name}</div><span className="metric-hint">{fund.category ?? C.unknownCategory}</span></DataTableCell>
            <DataTableCell><span className="metric-value" title={fund.d1.statistic ?? undefined}>{percent(fund.d1.statistic, 4)}</span></DataTableCell>
            <DataTableCell><span className="metric-value" title={fund.d1.threshold ?? undefined}>{percent(fund.d1.threshold, 4)}</span></DataTableCell>
            <DataTableCell><Chip variant={variant(fund)}>{d1StateLabel(fund)}</Chip></DataTableCell>
            <DataTableCell className="comment-cell"><Comment fund={fund}/></DataTableCell>
          </DataTableRow>)}</DataTableBody>
        </DataTable>
      </div>
      <div className="mobile-funds">{filtered.map(fund => <article className="mobile-fund" key={fund.code} data-code={fund.code}>
        <div className="mobile-fund-head"><div><Link href={href(fund.code)} className="fund-code" style={{display: 'inline-flex', minHeight: 44, alignItems: 'center'}}>{fund.code} ↗</Link><div className="fund-name">{fund.name}</div><span className="metric-hint">{fund.category ?? C.unknownCategory}</span></div><Chip variant={variant(fund)}>{d1StateLabel(fund)}</Chip></div>
        <p><Comment fund={fund}/></p>
        <div className="mobile-metrics"><div><span className="metric-hint">{C.columnD1}</span><span className="metric-value">{percent(fund.d1.statistic, 4)}</span></div><div><span className="metric-hint">{C.columnThreshold}</span><span className="metric-value">{percent(fund.d1.threshold, 4)}</span></div></div>
      </article>)}</div>
    </>}
    <details className="qualification-panel"><summary>{C.thresholdHeading}</summary><p>{C.thresholdText}</p><p>{C.thresholdUniverse}</p></details>
    <details className="detail-note"><summary>{C.bundleVersion}</summary><code className="source-hash">{synthetic ? C.sampleVersion : list.immutable_bundle_id}</code></details>
    <details className="detail-note"><summary>{C.indexVersion}</summary><code className="source-hash">{synthetic ? C.sampleVersion : list.index_id}</code></details>
  </div>;
}
