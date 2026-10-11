'use client';
import Link from 'next/link';
import AssetLogo from '@/components/AssetLogo';
import {explainResult} from '@/lib/method-explanations';
import {useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {dateTr,decimal,post,reasonTr} from '@/lib/client';
import {sourceTime,sourceName,signalName} from '@/lib/fund-display';
import {notifyNotificationsChanged} from '@/lib/notification-events';
import WatchlistButton from './WatchlistButton';
import './watchlist.css';

export type WatchSignal={fund_code:string;name:string;detector_id:string;reason:string;value:string|null;threshold:string|null;evidence_id:string;as_of:string;effective_date:string|null;available_at:string;unit:string;read_at:string|null;source_references:{source_id:string|null;source_sha256:string|null;available_at:string|null}[]};
export type WatchData={items:{fund_code:string;name:string;category:string|null;saved_at:string;triggered_count:number;signal_count:number;abstained_count:number}[];signals:WatchSignal[];total:number;as_of:string|null;run_created_at:string|null;run_id:string|null;notifications_enabled:boolean;data_mode:string};
export type NotificationData={items:WatchSignal[];total:number;unread:number;limit:number;offset:number;as_of:string|null;run_created_at:string|null;notifications_enabled:boolean;data_mode:string};

function evidenceHref(signal:WatchSignal){return `/developments/${encodeURIComponent(signal.evidence_id)}?fund=${encodeURIComponent(signal.fund_code)}`;}

export function NotificationPreferences({enabled}:{enabled:boolean}){
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[current,setCurrent]=useState(enabled);const router=useRouter();
  useEffect(()=>setCurrent(enabled),[enabled]);
  async function change(){const next=!current;setCurrent(next);setBusy(true);setError('');try{const result=await post('/notifications/preferences',{enabled:next});if(!result.ok)throw new Error();notifyNotificationsChanged();router.refresh();}catch{setCurrent(!next);setError('Tercih kaydedilemedi. Tekrar deneyin.');}finally{setBusy(false);}}
  return <aside className="watch-side-card" id="notification-preferences"><h2>Bildirim tercihleri</h2><div className="watch-info-row"><span>Kanal</span><span>Uygulama içi</span></div><label className="watch-info-row watch-switch"><span>İnceleme bulguları</span><input type="checkbox" checked={current} disabled={busy} onChange={change}/><span>{current?'Açık':'Kapalı'}</span></label><p className="watch-small">Takip edilen fonların son tamamlanan analizindeki bulgular gösterilir.</p>{error&&<p role="alert" className="watch-error">{error}</p>}</aside>;
}

function EmptyFindings({data}:{data:WatchData}){
  const evaluated=data.items.filter(item=>item.signal_count>0),missing=evaluated.filter(item=>item.abstained_count>0),unexamined=data.items.length-evaluated.length;
  const title=evaluated.length===0?'Bu fonlar için tamamlanmış inceleme yok.':missing.length||unexamined?'İnceleme işareti yok; bazı bilgiler eksik.':'Tamamlanan karşılaştırmalarda inceleme işareti oluşmadı.';
  return <div className="watch-empty"><span className="watch-empty-icon"><img src="/figma-watchlist/empty-info.svg" alt=""/></span><h3>{title}</h3><p>{evaluated.length===0?'Fon sayfalarından hangi kaynakların mevcut olduğunu inceleyebilirsiniz.':`${evaluated.length} fonda kayıtlı inceleme var.${missing.length?` ${missing.length} fonda bazı karşılaştırmalar için bilgi yetersiz.`:''}${unexamined?` ${unexamined} fonda henüz inceleme kaydı yok.`:''}`} Bu durum fonların güvenli olduğu anlamına gelmez.</p></div>;
}

export function WatchlistContent({data}:{data:WatchData}){
  const [onlyFindings,setOnlyFindings]=useState(false);
  const changed=data.items.filter(item=>item.triggered_count>0);
  const items=onlyFindings?changed:data.items;
  return <div className="watch-page">
    <div className="watch-title"><div><h1>Takip listem</h1><p>Takip listesinde {data.total} fon var.{data.signals.length>0&&<> Son tamamlanan analizde {data.signals.length} inceleme bulgusu bulunuyor.</>}</p></div><Link className="watch-button" href="/funds"><img src="/figma-watchlist/plus.svg" alt=""/>Fon ekle</Link></div>
    <div className="watch-columns"><div className="watch-main">
      {data.total===0?<div className="watch-empty"><span className="watch-empty-icon"><img src="/figma-watchlist/bookmark-large.svg" alt=""/></span><h3>Takip listeniz henüz boş.</h3><p>Fonları adı veya koduyla bulun ve takip listenize ekleyin.</p><Link className="watch-button" href="/funds">Fonları keşfet</Link></div>:<>
        {data.signals.length===0?<><EmptyFindings data={data}/><h2 className="watch-section-title">Takip edilen fonlar</h2></>:<div className="watch-segments" aria-label="Takip listesi filtresi"><button type="button" aria-pressed={!onlyFindings} onClick={()=>setOnlyFindings(false)}>Tümü ({data.total})</button><button type="button" aria-pressed={onlyFindings} onClick={()=>setOnlyFindings(true)}>Bulgusu olanlar ({changed.length})</button></div>}
        <div className="watch-fund-list">{items.map(item=><div className="watch-fund-row" key={item.fund_code}><AssetLogo kind="fund" code={item.fund_code} name={item.name} decorative/><Link className="watch-fund-name" href={`/funds/${item.fund_code}`}><strong>{item.fund_code}</strong><span>{item.name}</span></Link><span className="watch-fund-state">{item.triggered_count>0?`${item.triggered_count} inceleme bulgusu`:item.signal_count===0?'Analiz bulunmuyor':item.abstained_count>0?`${item.abstained_count} incelemede bilgi eksik`:'Karşılaştırmalar tamamlandı'}</span><WatchlistButton code={item.fund_code} initialSaved/></div>)}</div>
        {data.signals.length>0&&<section className="watch-developments"><h2>Bu listedeki son bulgular</h2>{data.signals.map(signal=><article className="watch-development" key={signal.evidence_id}><time dateTime={signal.available_at}>{sourceTime(signal.available_at)}</time><div><span className="watch-badge">İnceleme bulgusu</span><span className="watch-neutral">{signalName(signal.detector_id)}</span><h3>{signal.fund_code}: {explainResult({...signal,state:'TRIGGERED'})}</h3><div className="watch-source"><span>Kaynak: {Array.from(new Set(signal.source_references.map(source=>sourceName(source.source_id)))).join(', ')||'Kaynak kaydı bulunmuyor'}</span><span>Gözlem: {dateTr(signal.effective_date)}</span><Link href={evidenceHref(signal)}>Kanıtı incele <img src="/figma-watchlist/chevron.svg" alt=""/></Link></div></div></article>)}</section>}
      </>}
    </div><div className="watch-sidebar"><NotificationPreferences enabled={data.notifications_enabled}/><aside className="watch-side-card"><h2>Veri durumu</h2><div className="watch-info-row"><span>Son veri tarihi</span><span>{data.as_of?dateTr(data.as_of):'Analiz yok'}</span></div><div className="watch-info-row"><span>Hesaplama zamanı</span><span>{data.run_created_at?sourceTime(data.run_created_at):'Analiz yok'}</span></div><p className="watch-small">Her bulgunun kaynağı ve kullanılabilirlik zamanı fonun kanıt kayıtlarında bulunur. </p></aside></div></div></div>;
}

export function NotificationsContent({data,unreadOnly}:{data:NotificationData;unreadOnly:boolean}){
  const [busy,setBusy]=useState(false),[error,setError]=useState('');const router=useRouter();
  async function read(ids?:string[]){setBusy(true);setError('');try{const response=await post(ids?'/notifications/read':'/notifications/read-all',ids?{evidence_ids:ids}:{});if(!response.ok)throw new Error();notifyNotificationsChanged();router.refresh();}catch{setError('Okunma durumu kaydedilemedi. Sayfayı yenileyip tekrar deneyin.');}finally{setBusy(false);}}
  return <div className="watch-page"><div className="watch-title"><h1>Bildirimler</h1><div className="watch-title-actions"><button type="button" className="watch-text-button" disabled={busy||data.unread===0} onClick={()=>read()}>Tümünü okundu say</button><a className="watch-settings" href="#notification-preferences" aria-label="Bildirim tercihleri"><img src="/figma-watchlist/settings.svg" alt=""/></a></div></div>
    <div className="watch-columns"><div className="watch-main"><div className="watch-segments"><Link aria-current={!unreadOnly?'page':undefined} href="/notifications">Tümü</Link><Link aria-current={unreadOnly?'page':undefined} href="/notifications?unread=1">Okunmamış ({data.unread})</Link></div>{error&&<p role="alert" className="watch-error">{error}</p>}
      {data.items.length===0?<div className="watch-empty"><span className="watch-empty-icon"><img src="/figma-watchlist/empty-info.svg" alt=""/></span><h3>{!data.notifications_enabled?'Uygulama içi bildirimler kapalı.':unreadOnly?'Okunmamış bildirim yok.':'Gösterilecek bildirim yok.'}</h3><p>{!data.notifications_enabled?'Bildirimleri tercihler bölümünden açabilirsiniz.':'Bildirimler takip ettiğiniz fonların son tamamlanan analizindeki bulgulardan oluşur.'}</p><Link href="/watchlist">Takip listeme git</Link></div>:data.items.map(item=><article className={`watch-notification ${item.read_at?'is-read':''}`} key={item.evidence_id}><time dateTime={item.available_at}>{sourceTime(item.available_at)}</time><div className="watch-notification-title"><Link href={evidenceHref(item)}>{item.fund_code}: {explainResult({...item,state:'TRIGGERED'})}</Link>{!item.read_at&&<img src="/figma-watchlist/unread.svg" alt="Okunmamış"/>}</div><p>{signalName(item.detector_id)}</p><div className="watch-notification-actions"><Link href={evidenceHref(item)}>Kaynağı ve kanıtı incele</Link>{!item.read_at&&<button className="watch-text-button" type="button" disabled={busy} onClick={()=>read([item.evidence_id])}>Okundu say</button>}</div></article>)}
      {(data.offset>0||data.offset+data.items.length<data.total)&&<nav className="watch-pagination" aria-label="Bildirim sayfaları">{data.offset>0&&<Link href={`/notifications?unread=${unreadOnly?1:0}&offset=${Math.max(0,data.offset-data.limit)}`}>Önceki</Link>}{data.offset+data.items.length<data.total&&<Link href={`/notifications?unread=${unreadOnly?1:0}&offset=${data.offset+data.limit}`}>Sonraki</Link>}</nav>}
    </div><div className="watch-sidebar"><NotificationPreferences enabled={data.notifications_enabled}/></div></div></div>;
}
