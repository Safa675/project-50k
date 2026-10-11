import Link from 'next/link';
import type {Metadata} from 'next';
import {serverApi} from '@/lib/auth';
import KapExperiment from '@/components/KapExperiment';
import ResultsReport from './ResultsReport';
import styles from './results.module.css';

export const metadata:Metadata={title:'Sonuçlar · BlackSwan'};

export default async function Results(){
  const response=await serverApi('/evaluation/retrospective');
  if(response.status===404)return <div className={styles.page}><header className={styles.hero}><span className={styles.eyebrow}>Geriye dönük karşılaştırma</span><h1>12 Eylül taraması</h1><p>Bu tarihe ait tamamlanmış tarama kaydı bulunamadığı için bir sonuç hesaplanamıyor.</p><Link href="/method">Yöntemi inceleyin</Link></header></div>;
  if(!response.ok)throw new Error('Karşılaştırma sonuçları yüklenemiyor.');
  return <ResultsReport report={await response.json()} experimentPanel={<KapExperiment/>}/>;
}
