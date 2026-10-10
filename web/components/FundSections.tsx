'use client';

import {useState} from 'react';
import {useReady} from '@/lib/use-ready';
import styles from './Funds.module.css';

export default function FundSections({overview, evidence, sources}: {
  overview: React.ReactNode; evidence: React.ReactNode; sources: React.ReactNode;
}) {
  const [tab, setTab] = useState('overview');
  const ready = useReady();
  return <>
    <div className={styles.segments} role="tablist" aria-label="Fon bölümleri">
      {([['overview', 'Genel bakış'], ['evidence', 'Gelişmeler'], ['sources', 'Kaynaklar']] as const).map(([id, label]) =>
        <button disabled={!ready} key={id} id={`tab-${id}`} type="button" role="tab" aria-selected={tab === id} aria-controls={`panel-${id}`}
          className={tab === id ? styles.selected : ''} tabIndex={tab === id ? 0 : -1}
          onKeyDown={event => {
            if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
            event.preventDefault();
            const tabs = ['overview', 'evidence', 'sources'];
            const next = tabs[(tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : 2)) % tabs.length];
            setTab(next); document.getElementById(`tab-${next}`)?.focus();
          }} onClick={() => setTab(id)}>{label}</button>)}
    </div>
    <div id="panel-overview" role="tabpanel" aria-labelledby="tab-overview" hidden={tab !== 'overview'}>{overview}</div>
    <div id="panel-evidence" role="tabpanel" aria-labelledby="tab-evidence" hidden={tab !== 'evidence'}>{evidence}</div>
    <div id="panel-sources" role="tabpanel" aria-labelledby="tab-sources" hidden={tab !== 'sources'}>{sources}</div>
  </>;
}
