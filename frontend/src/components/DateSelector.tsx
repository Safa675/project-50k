'use client';
import Form from 'next/form';
import {useId} from 'react';
import {DATED_COPY as C, DATED_EXACT as S, dateOptionLabel} from '@/lib/dated-presentation';
import {selectClass} from './primitives/form';

/**
 * GET form over the sealed dates only. Changing the select never navigates;
 * the explicit "Tarihi göster" submit does (WCAG 2.2 SC 3.2.2).
 */
export default function DateSelector({dates, selected, windowEnd, action}: {
  dates: readonly string[]; selected: string; windowEnd: string; action: string;
}) {
  const id = useId();
  const hintId = `${id}-hint`;
  return <Form action={action} className="date-selector" aria-label={C.selectorForm}
    style={{display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', gap: 12, margin: '0 0 22px', padding: '14px 16px', border: '1px solid var(--border-subtle)', borderRadius: 8, background: '#fff', maxWidth: '100%'}}>
    <div style={{display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0, flex: '1 1 260px', maxWidth: 520}}>
      <label htmlFor={id} style={{fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600}}>{C.selectorLabel}</label>
      <select id={id} name="date" key={selected} defaultValue={selected} aria-describedby={hintId} className={selectClass}
        style={{minHeight: 44, width: '100%', minWidth: 0, maxWidth: '100%', textOverflow: 'ellipsis'}}>
        {dates.map(date => <option key={date} value={date}>{dateOptionLabel(date, windowEnd)}</option>)}
      </select>
    </div>
    <button type="submit" className="button primary" style={{minHeight: 44, minWidth: 44}}>{C.selectorSubmit}</button>
    <p id={hintId} className="detail-note" style={{flexBasis: '100%', margin: 0}}>{C.selectorHint}</p>
    <details className="detail-note" style={{flexBasis: '100%'}}>
      <summary style={{cursor: 'pointer', minHeight: 44, display: 'flex', alignItems: 'center', fontWeight: 600}}>{S.whyDatesTitle}</summary>
      <p style={{margin: '4px 0 0'}}>{S.whyDates}</p>
    </details>
  </Form>;
}
