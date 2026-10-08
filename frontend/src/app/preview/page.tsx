import FundList from '@/components/FundList';
import FundDetail from '@/components/FundDetail';
import Shell from '@/components/Shell';
import type {FindingFilter} from '@/lib/presentation';
import EmptyState from '@/components/primitives/EmptyState';
import {syntheticFunds,syntheticSummary,syntheticSources} from '@/lib/synthetic';
export default async function Preview({searchParams}:{searchParams:Promise<Record<string,string|undefined>>}) {
 const query=await searchParams;
 if(query.state==='error')return <Shell synthetic><div className="notice error-panel"><strong>Araştırma verisi alınamadı.</strong><p>Yerel araştırma API’sine ulaşılamıyor. Hiçbir fon sonucu gösterilemiyor.</p><a className="button" href="/preview">Tekrar dene</a></div></Shell>;
 if(query.state==='loading')return <Shell synthetic><EmptyState title="Araştırma verisi yükleniyor…" description="Seçili arşiv paketi hazırlanıyor."/></Shell>;
 const fund=syntheticFunds.find(f=>f.code===query.detail);
 const backParams=new URLSearchParams();for(const key of ['q','category','finding'])if(query[key])backParams.set(key,query[key]);
 if(fund)return <FundDetail fund={fund} sources={fund.code==='AAA'?syntheticSources:[]} backQuery={backParams.toString()} synthetic/>;
 return <FundList funds={syntheticFunds} summary={syntheticSummary} synthetic initialQuery={query.q??''} initialCategory={query.category??''} initialFinding={['all','two','one','unavailable','none'].includes(query.finding??'')?query.finding as FindingFilter:'all'}/>;
}
