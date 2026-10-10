'use client';
import {useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {csrfCookie,post} from '@/lib/client';
import {notifyNotificationsChanged} from '@/lib/notification-events';
import './watchlist.css';

export default function WatchlistButton({code,initialSaved}:{code:string;initialSaved?:boolean}) {
  const [saved,setSaved]=useState(initialSaved??false),[ready,setReady]=useState(initialSaved!==undefined);
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const router=useRouter();
  useEffect(()=>{if(initialSaved!==undefined){setSaved(initialSaved);setReady(true);return;}
    const abort=new AbortController();
    fetch('/api/p/watchlist',{cache:'no-store',signal:abort.signal}).then(async response=>{
      if(response.status===401){setReady(true);return;}
      if(!response.ok)throw new Error();
      const data=await response.json();setSaved(data.items.some((item:{fund_code:string})=>item.fund_code===code));setReady(true);
    }).catch(()=>{if(!abort.signal.aborted)setError('Takip durumu alınamadı. Sayfayı yenileyin.');});
    return()=>abort.abort();},[code,initialSaved]);
  async function toggle(){setBusy(true);setError('');
    try{const response=saved?await fetch(`/api/p/watchlist/${encodeURIComponent(code)}`,{method:'DELETE',headers:{'X-CSRF-Token':csrfCookie()},cache:'no-store'}):await post(`/watchlist/${encodeURIComponent(code)}`);
      if(response.status===401){router.push('/login');return;}
      if(!response.ok){setError(response.status===409?'Takip listesi en fazla 100 fon içerebilir.':'Takip listesi güncellenemedi. Tekrar deneyin.');return;}
      setSaved(!saved);notifyNotificationsChanged();router.refresh();
    }catch{setError('Bağlantı kurulamadı. Tekrar deneyin.');}finally{setBusy(false);}}
  return <span className="watch-button-wrap"><button className="watch-button" type="button" onClick={toggle} disabled={!ready||busy} aria-pressed={saved} aria-label={`${code}: ${saved?'Takipten çıkar':'Takip et'}`}><img src="/figma-watchlist/bookmark.svg" alt=""/>{busy?'Kaydediliyor…':saved?'Takip ediliyor':'Takip et'}</button>{error&&<span role="alert" className="watch-error">{error}</span>}</span>;
}
