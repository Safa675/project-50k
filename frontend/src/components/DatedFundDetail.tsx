'use client';
import Link from 'next/link';
import type {Ref} from 'react';
import type {DatedDetailResponse, DatedSource} from '@/lib/dated-contract';
import {DATED_COPY as C, DATED_EXACT as S, commentWithNote, d1StateLabel, datedListHref, datedReason, fixedViewHref,
  formatCutoff, formatDay} from '@/lib/dated-presentation';
import {percent, sourceTitle} from '@/lib/presentation';
import Chip from './primitives/Chip';
import EmptyState from './primitives/EmptyState';
import FundChart from './FundChart';

function SourceEntry({source}: {source: DatedSource}) {
  // No dates are shown: retrieval instants postdate every selectable cutoff.
  return <div className="evidence-source">
    <strong>{sourceTitle(source)}</strong>
    <details className="detail-note source-version"><summary>{C.sourceVersion}</summary><p>{C.sourceDigest}</p><code className="source-hash">{source.sha256}</code></details>
  </div>;
}

/** D1 panel for one fund at one sealed date. The date is read-only here. */
export default function DatedFundDetail({detail, synthetic = false, headingRef, windowEnd}: {
  detail: DatedDetailResponse; synthetic?: boolean; headingRef?: Ref<HTMLHeadingElement>; windowEnd: string;
}) {
  const {fund, sources} = detail;
  const date = detail.cutoff_date;
  const d1 = fund.d1;
  const primary = sources.filter(source => source.kind === 'PRICE' && source.fund_code === fund.code);
  const peers = sources.filter(source => source.kind === 'PRICE' && source.fund_code !== fund.code);
  const versions = sources.filter(source => source.kind !== 'PRICE');
  return <div data-dated-date={date} data-dated-bundle={detail.immutable_bundle_id}>
    <Link href={datedListHref(date, detail.immutable_bundle_id, synthetic)} className="back-link" style={{minHeight: 44, display: 'inline-flex', alignItems: 'center', marginBottom: 14}}>{C.backToList}</Link>
    <section className="page-intro">
      <div><p className="eyebrow">{fund.category ?? C.unknownCategory}</p><h1 ref={headingRef} tabIndex={-1}>{fund.code} <span className="text-xl font-normal text-[var(--text-secondary)]">{fund.name}</span></h1></div>
      <div className="cutoff"><span>{C.cutoffCaption}</span>{formatCutoff(detail.cutoff_at)}
        <small className="detail-note" style={{display: 'block', marginTop: 6}}>{C.dateReadOnly}</small>
        {date === windowEnd && <small className="detail-note" style={{display: 'block'}}>{S.windowEnd}</small>}</div>
    </section>
    <div className="detail-summary">{commentWithNote(fund).map(text => <p key={text} style={{margin: '0 0 6px'}}>{text}</p>)}</div>
    {!fund.date_context.has_positive_price_on_or_before_cutoff && <p className="notice">{C.noPriceDetail}</p>}
    <div className="detail-layout">
      <div>
        <section className="detail-section">
          <h2>{C.chartHeading}</h2>
          <FundChart chart={fund.chart} synthetic={synthetic}/>
          {fund.chart.status === 'AVAILABLE' && <p className="detail-note">{C.chartNote}</p>}
        </section>
        <section className="detail-section">
          <div className="metric-panel">
            <h2>{C.d1Heading}</h2>
            <p className="detail-note">{C.d1Description}</p>
            <Chip variant={fund.d1_state === 'ELIGIBLE_CROSSING' ? 'warning' : 'outline'}>{d1StateLabel(fund)}</Chip>
            <span className="metric-value" title={d1.statistic ?? undefined}>{percent(d1.statistic, 4)}</span>
            <dl>
              <div><dt>{C.labelThreshold}</dt><dd title={d1.threshold ?? undefined}>{percent(d1.threshold, 4)}</dd></div>
              <div><dt>{C.labelPeriod}</dt><dd>{d1.metric_period.start ? formatDay(d1.metric_period.start) : C.unknown} – {d1.metric_period.end ? formatDay(d1.metric_period.end) : C.unknown}</dd></div>
              <div><dt>{C.labelUsable}</dt><dd>{d1.usable_observations} / {d1.window_positions}</dd></div>
              <div><dt>{C.labelPeers}</dt><dd>{C.peersPrefix}{d1.eligible_peers}{C.ofFunds}</dd></div>
              <div><dt>{C.labelLatest}</dt><dd>{d1.latest_contributing_at ? formatDay(d1.latest_contributing_at) : C.unknown}</dd></div>
            </dl>
            {[...new Set(d1.missing_reasons.map(datedReason))].map(value => <p className="detail-note" key={value}>{value}</p>)}
            {d1.qualifications.length > 0 && <details className="qualification-panel"><summary>{C.qualificationsPrefix}({d1.qualifications.length})</summary>
              <ul>{[...new Set(d1.qualifications.map(datedReason))].map(value => <li key={value}>{value}</li>)}</ul></details>}
            <details className="detail-note"><summary>{C.labelExact}</summary><p>{C.labelStatistic}: <code>{d1.statistic ?? C.unknown}</code><br/>{C.labelExactThreshold}: <code>{d1.threshold ?? C.unknown}</code></p></details>
          </div>
        </section>
        <section className="detail-section">
          <h2>{C.notComputedHeading}</h2>
          <p className="detail-note">{S.notComputed}</p>
          <Link href={fixedViewHref(synthetic)} className="source-link">{S.fixedViewLink}</Link>
        </section>
      </div>
      <aside>
        <section className="detail-section">
          <h2>{C.sourcesHeading}</h2>
          <p className="detail-note">{C.sourcesNote}</p>
          {primary.length === 0 ? <EmptyState title={C.noSources} description={C.noSourcesDescription}/> : primary.map(source => <SourceEntry source={source} key={source.source_id}/>)}
          {peers.length > 0 && <details className="evidence-group"><summary>{C.peerSources} ({peers.length})</summary>{peers.map(source => <SourceEntry source={source} key={source.source_id}/>)}</details>}
          {versions.length > 0 && <details className="evidence-group"><summary>{C.otherSources} ({versions.length})</summary>{versions.map(source => <SourceEntry source={source} key={source.source_id}/>)}</details>}
        </section>
        <div className="notice"><strong>{C.limitHeading}</strong><br/>{C.limitText}</div>
        <p className="detail-note">{C.production}</p>
        <details className="detail-note"><summary>{C.bundleVersion}</summary><code className="source-hash">{synthetic ? C.sampleVersion : detail.immutable_bundle_id}</code></details>
      </aside>
    </div>
  </div>;
}
