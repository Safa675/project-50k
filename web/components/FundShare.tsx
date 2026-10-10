'use client';

import {useState} from 'react';
import {useReady} from '@/lib/use-ready';
import styles from './Funds.module.css';

export default function FundShare() {
  const [status, setStatus] = useState('');
  const ready = useReady();
  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setStatus('Bağlantı kopyalandı.');
    } catch {setStatus('Bağlantı kopyalanamadı; adres çubuğundan kopyalayabilirsiniz.');}
  }
  return <span className={styles.share}><button disabled={!ready} className={styles.iconButton} type="button" aria-label="Fon bağlantısını kopyala" onClick={share}>
    <img src="/figma/funds/share.svg" alt=""/>
  </button>{status && <span className={styles.shareStatus} role="status">{status}</span>}</span>;
}
