'use client';

import {useId, useState} from 'react';
import {useReady} from '@/lib/use-ready';
import styles from './Funds.module.css';

export default function FundTooltip({children, title, text, pill = false, align = 'start'}: {
  children: React.ReactNode; title: string; text: string; pill?: boolean; align?: 'start'|'end';
}) {
  const id = useId();
  const ready = useReady();
  const [open, setOpen] = useState(false);
  return <span className={styles.tooltipHost} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
    <button disabled={!ready} type="button" className={pill ? styles.mode : styles.tooltipTrigger} aria-describedby={open ? id : undefined}
      aria-expanded={open} onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
      onKeyDown={event => {if (event.key === 'Escape') setOpen(false);}} onClick={() => setOpen(true)}>{children}</button>
    {open && <span id={id} role="tooltip" className={`${styles.tooltip} ${align === 'end' ? styles.tooltipEnd : ''}`}>
      <img className={styles.tooltipArrow} src="/figma/funds/tooltip-up.svg" alt=""/>
      <strong>{title}</strong><span>{text}</span>
    </span>}
  </span>;
}
