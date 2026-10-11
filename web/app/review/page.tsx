import Link from 'next/link';
import {requireUser,serverApi} from '@/lib/auth';
import {dateTr} from '@/lib/client';
import ReviewQueue from '@/components/review/ReviewQueue';
import type {Decision} from '@/components/review/review-logic';
import styles from '@/components/review/review.module.css';

/** The analyst review queue: pending proposals of the selected analysis, and the ones a human already reviewed. */
export default async function Review({searchParams}:{searchParams:Promise<{durum?:string|string[]}>}){
  const user=await requireUser();
  if(user.role==='viewer')return <section className={styles.page}><header className={styles.header}><h1>İnceleme yetkisi gerekiyor</h1><p className={styles.intro}>Bu bölüm analist ve yönetici kullanıcılar içindir.</p></header></section>;
  const reviewedTab=(await searchParams).durum==='incelenen';
  const [queueResponse,allResponse]=await Promise.all([serverApi('/review'),serverApi('/decisions')]);
  if(!queueResponse.ok)throw new Error('İnceleme kuyruğu yüklenemiyor.');
  const pending:Decision[]=(await queueResponse.json()).items;
  const reviewed:Decision[]|null=allResponse.ok?((await allResponse.json()).items as Decision[]).filter(item=>item.has_current_review):null;
  const context=user.analysis_context;
  return <section className={styles.page}>
    <header className={styles.header}>
      <h1>İnceleme kuyruğu</h1>
      <p className={styles.intro}>Ajan ekibinin ve yapay zekânın önerileri, kurala dayalı sonuçlardan ayrı gösterilir. Son karar insanda: öneriyi kabul edin, gerekçeyle değiştirin veya reddedin. Her inceleme kaydedilir; ilk öneri ve önceki kararlar korunur. Bir öneri usulsüzlük tespiti değildir.</p>
      {context&&<p className={styles.context}>Seçili analiz tarihi: {dateTr(context.as_of_date)}. Kuyrukta yalnızca bu analize ait öneriler yer alır.</p>}
    </header>
    <nav className={styles.tabs} aria-label="İnceleme durumu">
      <Link className={styles.tab} href="/review" aria-current={reviewedTab?undefined:'page'}>Bekleyen <span className={styles.count}>{pending.length}</span></Link>
      <Link className={styles.tab} href="/review?durum=incelenen" aria-current={reviewedTab?'page':undefined}>İncelenen {reviewed&&<span className={styles.count}>{reviewed.length}</span>}</Link>
    </nav>
    {reviewedTab&&!reviewed
      ?<div className={styles.empty} role="alert"><p>İncelenen kayıtlar şu anda yüklenemiyor. Sayfayı yenileyip yeniden deneyin.</p><Link href="/review">Bekleyen önerilere dönün</Link></div>
      :<ReviewQueue key={reviewedTab?'reviewed':'pending'} items={reviewedTab?reviewed??[]:pending} reviewedTab={reviewedTab}/>}
  </section>;
}
