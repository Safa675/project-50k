'use client';

import {useId} from 'react';
import {AGENTS_OPEN} from '@/lib/agents';
import {type FundSignal, signalName} from '@/lib/fund-display';
import styles from './FundAlert.module.css';

// The fund page's first summary: what the selected date's calculation flagged, the agent
// team's case and the decision state. Every sentence comes from the server or from fixed
// copy below; a warning is a reason to review, never a conclusion about the fund.

export type Calculation = 'none' | 'not_covered' | 'triggered' | 'limited' | 'clear';
export type SummaryMeasure = {detector_id: string; label_tr: string; fact_tr: string | null; effective_date: string | null};
export type SummaryHighlight = {test: string; name_tr: string; detail_tr: string};
export type SummaryDecision = {proposal_tr: string | null; effective_tr: string | null; human_reviewed: boolean; decided_by: 'HUMAN' | 'AI'};
export type SummaryCase = {case_id: string; status: 'open' | 'investigating' | 'reported'; status_tr: string; stage_tr: string | null;
  opened_by: 'sentinel' | 'user' | null; highlights: SummaryHighlight[]; decision: SummaryDecision | null};
// `team` is undefined when the case could not be read (older or unreachable service): nothing is claimed then.
export type FundSummary = {calculation: Calculation; as_of: string | null; triggered: SummaryMeasure[]; team?: SummaryCase | null};

const CALCULATIONS = new Set<string>(['none', 'not_covered', 'triggered', 'limited', 'clear']);
const CASE_STATUS: Record<string, string> = {open: 'Açık', investigating: 'İnceleniyor', reported: 'Raporlandı'};
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;

function record(value: unknown): value is Record<string, unknown> {return typeof value === 'object' && value !== null && !Array.isArray(value);}
function text(value: unknown, max: number): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed && trimmed.length <= max ? trimmed : null;
}
function day(value: unknown): string | null {return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value) ? value.slice(0, 10) : null;}

function parseCase(value: unknown): SummaryCase | null {
  if (!record(value) || typeof value.case_id !== 'string' || !UUID.test(value.case_id)) return null;
  const status = value.status;
  if (status !== 'open' && status !== 'investigating' && status !== 'reported') return null;
  const highlights = Array.isArray(value.highlights) ? value.highlights.slice(0, 3).flatMap(item => {
    if (!record(item)) return [];
    const test = text(item.test, 40), name = text(item.name_tr, 120), detail = text(item.detail_tr, 1200);
    return test && name && detail ? [{test, name_tr: name, detail_tr: detail}] : [];
  }) : [];
  const decision = record(value.decision) ? {proposal_tr: text(value.decision.proposal_tr, 120),
    effective_tr: text(value.decision.effective_tr, 120), human_reviewed: value.decision.human_reviewed === true,
    decided_by: value.decision.decided_by === 'HUMAN' ? 'HUMAN' as const : 'AI' as const} : null;
  return {case_id: value.case_id, status, status_tr: text(value.status_tr, 40) ?? CASE_STATUS[status],
    stage_tr: text(value.stage_tr, 300), opened_by: value.opened_by === 'user' ? 'user' : value.opened_by === 'sentinel' ? 'sentinel' : null,
    highlights, decision};
}

/** Validates the /agents/funds/{code}/summary response; null when it is not usable. */
export function parseFundSummary(value: unknown): FundSummary | null {
  if (!record(value) || typeof value.calculation !== 'string' || !CALCULATIONS.has(value.calculation) || !Array.isArray(value.triggered)) return null;
  const triggered = value.triggered.slice(0, 12).flatMap(item => {
    if (!record(item)) return [];
    const detector = text(item.detector_id, 30), label = text(item.label_tr, 120);
    return detector && label ? [{detector_id: detector, label_tr: label, fact_tr: text(item.fact_tr, 400), effective_date: day(item.effective_date)}] : [];
  });
  const calculation = value.calculation === 'triggered' && !triggered.length ? 'clear' : value.calculation as Calculation;
  return {calculation, as_of: day(value.as_of), triggered, team: value.case === null ? null : parseCase(value.case) ?? null};
}

/** Fallback from the fund page's own signals when the summary service cannot be read; the case stays unknown. */
export function summaryFromSignals(signals: FundSignal[]): FundSummary {
  const measured = signals.filter(signal => !signal.is_attribute);
  const triggered = measured.filter(signal => signal.state === 'TRIGGERED' && signal.available_at !== null)
    .sort((a, b) => Number(b.detector_id === 'AN-FND-005') - Number(a.detector_id === 'AN-FND-005') || a.detector_id.localeCompare(b.detector_id))
    .map(signal => ({detector_id: signal.detector_id, label_tr: signalName(signal.detector_id), fact_tr: null, effective_date: day(signal.effective_date)}));
  const calculation: Calculation = triggered.length ? 'triggered' : !measured.length ? 'not_covered' :
    measured.every(signal => signal.state === 'ABSTAINED') ? 'limited' : 'clear';
  return {calculation, as_of: null, triggered, team: undefined};
}

function dateTr(value: string): string {
  return new Intl.DateTimeFormat('tr-TR', {day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Istanbul'}).format(new Date(`${value}T12:00:00+03:00`));
}

/** The decision line: a human decision wins; otherwise the team's proposal awaits human review. */
export function decisionLine(item: SummaryCase): {label: string; value: string; note: string | null} {
  const decision = item.decision;
  if (!decision) return {label: 'Karar durumu', value: 'Ekibin karar önerisi henüz hazır değil',
    note: 'Öneri hazır olduğunda son söz insan incelemesinde olacak.'};
  if (decision.human_reviewed) {
    const changed = decision.proposal_tr && decision.effective_tr && decision.proposal_tr !== decision.effective_tr;
    return {label: 'İnsan kararı', value: decision.effective_tr ?? 'Karar kaydedildi',
      note: changed ? `Ekibin önerisi “${decision.proposal_tr}” idi; insan incelemesi bunu değiştirdi.` : 'Ekibin önerisi insan tarafından incelendi.'};
  }
  return {label: 'Ekibin karar önerisi', value: decision.proposal_tr ?? 'Öneri kaydedildi', note: 'İnsan incelemesini bekliyor; son söz insanda.'};
}

/** Heading and lead sentence for a summary; neutral wording, no conclusion about the fund. */
export function summaryCopy(summary: FundSummary): {heading: string; lead: string} {
  const count = summary.triggered.length;
  if (summary.calculation === 'triggered') return {
    heading: summary.team ? 'Bu fon incelemeye alındı' : 'İnceleme sınırı aşıldı',
    lead: `Seçili tarihteki hesaplamada ${count.toLocaleString('tr-TR')} ölçüm inceleme sınırını aştı. Bu, fonun incelenmesi için bir gerekçedir; fon hakkında bir sonuç değildir.`};
  if (summary.calculation === 'clear') return {heading: 'Seçili tarihteki hesaplamada inceleme sınırı aşılmadı',
    lead: 'Bu bir güvence değildir; yalnızca incelenen ölçümleri anlatır.'};
  if (summary.calculation === 'limited') return {heading: 'Seçili tarihteki hesaplamada bu fon değerlendirilemedi',
    lead: 'Ölçümler için uygun tarihli bilgi yeterli değildi. Eksik bilgi, fonda inceleme gerektiren bir durum olmadığı anlamına gelmez.'};
  if (summary.calculation === 'not_covered') return {heading: 'Seçili tarihteki hesaplamada bu fon için kayıt yok',
    lead: 'Fon bu hesaplamanın kapsamında değildi. Kaydın olmaması, fonun incelendiği veya inceleme gerektirmediği anlamına gelmez.'};
  return {heading: 'Seçili tarih için tamamlanmış hesaplama yok',
    lead: 'Hesaplama tamamlandığında inceleme sınırını aşan ölçümler burada görünür.'};
}

function openPanel(detail: {tab: 'reporter'; caseId?: string}) {
  window.dispatchEvent(new CustomEvent(AGENTS_OPEN, {detail}));
}
// The decision block lives in the overview tab; show that tab before scrolling to it.
function goToDecision(event: React.MouseEvent<HTMLAnchorElement>) {
  const target = document.getElementById('karar');
  if (!target) return;
  event.preventDefault();
  const overview = document.getElementById('tab-overview');
  if (target.closest('[hidden]') && overview instanceof HTMLButtonElement) overview.click();
  window.requestAnimationFrame(() => {
    target.scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
    history.replaceState(null, '', '#karar');
  });
}

function Actions({team, decision}: {team: SummaryCase | null | undefined; decision: boolean}) {
  return <div className={styles.actions}>
    {team && <button type="button" className="bs-button bs-button-small" onClick={() => openPanel({tab: 'reporter', caseId: team.case_id})}>Vaka akışını aç</button>}
    {decision && <a className="bs-button bs-button-small bs-button-secondary" href="#karar" onClick={goToDecision}>İnsan kararına git</a>}
    <button type="button" className="bs-button bs-button-small bs-button-outline" onClick={() => openPanel({tab: 'reporter'})}>Raportöre sor</button>
  </div>;
}

function TeamBlock({team}: {team: SummaryCase}) {
  const decision = decisionLine(team);
  return <div className={styles.team}>
    <h3>Ajan ekibinin vakası</h3>
    <p className={styles.status}><span className={`${styles.pill} ${styles[`is-${team.status}`] ?? ''}`}>{team.status_tr}</span>
      {team.stage_tr && <span>{team.stage_tr}</span>}</p>
    {team.highlights.length > 0 && <div className={styles.tests}>
      <p className={styles.label}>Kodla hesaplanan test sonuçları</p>
      <ul>{team.highlights.map(item => <li key={item.test}><strong>{item.name_tr}</strong><span>{item.detail_tr}</span></li>)}</ul>
    </div>}
    <dl className={styles.decision}><dt>{decision.label}</dt><dd>{decision.value}</dd>{decision.note && <dd className={styles.note}>{decision.note}</dd>}</dl>
  </div>;
}

export default function FundAlert({summary, signals, canReview}: {summary: unknown; signals: FundSignal[]; canReview: boolean}) {
  const titleId = useId();
  const data = parseFundSummary(summary) ?? summaryFromSignals(signals);
  const copy = summaryCopy(data);
  const asOf = data.as_of ? `${dateTr(data.as_of)} hesaplaması` : 'Seçili tarihteki hesaplama';
  if (data.calculation !== 'triggered') {
    return <section className={styles.quiet} aria-labelledby={titleId}>
      <span className={styles.quietMark} aria-hidden="true"/>
      <div className={styles.quietText}>
        <h2 id={titleId}>{copy.heading}</h2>
        <p>{copy.lead}</p>
        {data.team && <p className={styles.quietCase}>Ajan ekibinin bu fon için bir vakası var: <strong>{data.team.status_tr}</strong>. {data.team.stage_tr}</p>}
      </div>
      {data.team && <Actions team={data.team} decision={canReview || Boolean(data.team.decision)}/>}
    </section>;
  }
  return <section className={styles.alert} aria-labelledby={titleId}>
    <header className={styles.head}>
      <span className={styles.mark} aria-hidden="true"><svg viewBox="0 0 24 24" focusable="false"><path d="M12 7v6M12 16.5v.5" strokeLinecap="round"/><circle cx="12" cy="12" r="9.25"/></svg></span>
      <div>
        <p className={styles.kicker}>{asOf}</p>
        <h2 id={titleId}>{copy.heading}</h2>
        <p className={styles.lead}>{copy.lead}</p>
      </div>
    </header>
    <div className={data.team === undefined ? styles.single : styles.body}>
      <div className={styles.measures}>
        <h3>İnceleme sınırını aşan ölçümler</h3>
        <ul>{data.triggered.map(item => <li key={item.detector_id}><strong>{item.label_tr}</strong>{item.fact_tr && <span>{item.fact_tr}</span>}
          {item.effective_date && <span className={styles.when}>İncelenen tarih: {dateTr(item.effective_date)}</span>}</li>)}</ul>
      </div>
      {data.team && <TeamBlock team={data.team}/>}
      {data.team === null && <div className={styles.team}>
        <h3>Ajan ekibinin vakası</h3>
        <p className={styles.note}>Bu tarih için henüz vaka açılmadı. Nöbetçi tamamlanmış hesaplamaları taradıkça inceleme sınırını aşan fonlar için vaka açar; Raportörden inceleme de isteyebilirsiniz.</p>
      </div>}
    </div>
    <Actions team={data.team} decision={canReview || Boolean(data.team?.decision)}/>
  </section>;
}
