import Link from 'next/link';
import {dateTr, decimal, reasonTr, stateTr} from '@/lib/client';
import {detectorNames, FundSignal} from '@/lib/fund-display';
import FundTooltip from './FundTooltip';
import styles from './Funds.module.css';

export default function FundEvidence({signals, showFund = false}: {signals: FundSignal[]; showFund?: boolean}) {
  return <div>{signals.length ? signals.map(signal => <div key={signal.evidence_id} className={styles.signalRow}>
    <div className={styles.signalDate}>{dateTr(signal.effective_date)}<p className={styles.caption}>Kanıt tarihi</p></div>
    <div className={styles.signalBody}>
      <div className={styles.signalTags}>
        <FundTooltip title={stateTr[signal.state] ?? signal.state} text={signal.state === 'TRIGGERED'
          ? 'Deterministik gösterge, sürümlenmiş kuralın eşiğini aştı. Bu bir geliştirme bulgusudur; fiyat yönü, usulsüzlük veya yatırım kararı belirtmez.'
          : signal.state === 'ABSTAINED' ? 'Göstergenin hesaplanması için yeterli ve uygun zamanlı kaynak bulunamadı. Eksik kanıt normal sonuç sayılmaz.'
          : 'Bu gösterge kendi eşik sınırını aşmadı. Diğer göstergeler ve kaynak sınırlamaları ayrıca değerlendirilmelidir.'}>
          <span className={`${styles.badge} ${signal.state === 'TRIGGERED' ? styles.triggered : ''}`}>
            {signal.state === 'TRIGGERED' && <img src="/design/important-dot.svg" alt=""/>}
            {signal.is_attribute ? 'Tarihçe özelliği' : stateTr[signal.state] ?? signal.state}
          </span>
        </FundTooltip><span className={styles.badge}>{signal.detector_id}</span>
      </div>
      <h3>{showFund && `${signal.fund_code}: `}{detectorNames[signal.detector_id] ?? signal.detector_id}</h3>
      <p>{reasonTr(signal.reason)}</p>
      <p>Değer: {decimal(signal.value)}{!signal.is_attribute && <> · Eşik: {decimal(signal.threshold)}</>}</p>
      <div className={styles.signalSources}>
        <span>Kaynak: {[...new Set(signal.source_references.map(ref => ref.source_id))].join(', ') || 'Uygun kaynak yok'}</span>
        <FundTooltip title="Kaynak dayanağı" text={signal.source_references.length
          ? 'Hesaplanan değer, aşağıdaki kaynak kimlikleri ve dosya özetleriyle izlenebilir. Bu kaynak sayısı, doğrulanmış başarı veya güven puanı değildir.'
          : 'Bu gösterge için uygun zamanlı bir kaynak referansı bulunmuyor. Kanıt yokluğu güvenli ya da riskli sonucuna çevrilmez.'}>
          {signal.source_references.length} kaynak referansı
        </FundTooltip>
        <Link className={styles.textButton} href={`/developments/${encodeURIComponent(signal.evidence_id)}?fund=${signal.fund_code}`}>Gelişmeyi incele<img src="/design/arrow.svg" alt=""/></Link>
      </div>
    </div>
  </div>) : <p className={styles.empty}>Bu görünüm için tamamlanmış detektör bulgusu bulunmuyor.</p>}</div>;
}
