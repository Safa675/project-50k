'use client';

import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {useEffect,useState} from 'react';
import type {User} from '@/lib/auth';
import {NOTIFICATIONS_CHANGED} from '@/lib/notification-events';
import SessionActions from './SessionActions';

export function ThemeToggle(){
  const [theme,setTheme]=useState<'dark'|'light'>('dark');
  useEffect(()=>{setTheme(document.documentElement.dataset.theme==='light'?'light':'dark');},[]);
  function toggle(){const next=theme==='dark'?'light':'dark';setTheme(next);document.documentElement.dataset.theme=next;try{localStorage.setItem('blackswan-theme',next);}catch{/* Theme still changes when browser storage is disabled. */}}
  return <button type="button" className={`bs-theme bs-theme-${theme}`} role="switch" aria-checked={theme==='light'} aria-label="Açık tema" onClick={toggle}><span className="bs-theme-track"><img className="bs-theme-base" src={`/design/${theme==='light'?'sun':'moon'}.svg`} alt=""/><span className="bs-theme-thumb"><img src={`/design/${theme==='light'?'sun':'moon'}-selected.svg`} alt=""/></span></span></button>;
}

export function SearchField({large=false,defaultValue=''}:{large?:boolean;defaultValue?:string}){
  return <form action="/funds" role="search" className={`bs-search${large?' bs-search-large':''}`}><img src={`/design/search-${large?'large':'small'}.svg`} alt=""/><label className="sr-only" htmlFor={large?'bs-hero-search':'bs-header-search'}>Fon adı ya da kodu ara</label><input id={large?'bs-hero-search':'bs-header-search'} name="q" type="search" maxLength={80} defaultValue={defaultValue} placeholder="Fon adı ya da kodu ara"/><button className="sr-only" type="submit">{large?'Fonları ara':'Katalogda ara'}</button></form>;
}

export function SiteHeader({user}:{user?:User}){
  const pathname=usePathname();
  const [unread,setUnread]=useState(0);
  useEffect(()=>{
    if(!user){setUnread(0);return;}
    let controller:AbortController|null=null;
    function refresh(){
      controller?.abort();const current=new AbortController();controller=current;setUnread(0);
      fetch('/api/p/notifications?limit=1',{cache:'no-store',signal:current.signal}).then(async response=>{
        if(!response.ok)return;const data=await response.json();
        if(!current.signal.aborted)setUnread(Number.isInteger(data.unread)&&data.unread>0?data.unread:0);
      }).catch(()=>{});
    }
    refresh();window.addEventListener(NOTIFICATIONS_CHANGED,refresh);
    return()=>{controller?.abort();window.removeEventListener(NOTIFICATIONS_CHANGED,refresh);};
  },[user?.user_id,pathname]);
  const links=[['/funds','Keşfet'],['/watchlist','Takip listem'],['/method','Yöntem']];
  return <header className="bs-header"><Link href="/" className="bs-brand" aria-label="BlackSwan ana sayfa"><span className="bs-logo"><img src={user?'/design/logo-auth.svg':'/design/logo.svg'} alt=""/></span><span><span className="bs-brand-light">Black</span><span className="bs-brand-medium">Swan</span></span></Link><nav className="bs-nav" aria-label="Ana gezinme">{links.map(([href,label])=><Link key={href} href={href} aria-current={pathname===href||pathname.startsWith(href+'/')?'page':undefined}>{label}</Link>)}</nav><div className="bs-header-search"><SearchField/></div><div className="bs-header-actions"><ThemeToggle/>{user?<><Link href="/notifications" className="bs-icon-button bs-notifications-link" aria-label={unread?`Bildirimler, ${unread} okunmamış`:'Bildirimler'}><img src="/design/bell.svg" alt=""/>{unread>0&&<img className="bs-notification-dot" src="/design/unread-dot.svg" alt=""/>}</Link><details className="bs-account"><summary aria-label="Hesap ve çalışma alanı"><span>{user.email.slice(0,2).toLocaleUpperCase('tr-TR')}</span></summary><div className="bs-account-menu"><p>{user.email}</p><Link href="/stocks">BIST 30 hisseleri</Link><Link href="/workflow">İş akışı ve API</Link>{user.role!=='viewer'&&<Link href="/review">İnceleme kuyruğu</Link>}<SessionActions/></div></details></>:<Link href="/login" className="bs-button bs-button-small bs-button-secondary">Giriş yap</Link>}</div></header>;
}

export function SiteFooter({dataMode}:{dataMode?:string}){
  return <footer className="bs-footer"><p>Gösterilen bilgiler yatırım tavsiyesi değildir. Bir gelişmenin gösterilmesi, fonun riskli ya da güvenli olduğu anlamına gelmez. Kaynak ve erişilebilirlik zamanı her kanıtla birlikte gösterilir.</p><p>{dataMode&&(dataMode==='SYNTHETIC'?'Sentetik test verisi · ':'Gecikmeli kaynak verisi · ')}Geliştirme sonucu · Veri hakları incelenmedi · Yatırım tavsiyesi değildir</p><div className="bs-footer-links"><Link href="/stocks">BIST 30</Link><Link href="/workflow">Kurumsal çalışma alanı ve API</Link></div></footer>;
}

export function DesignShell({children,user,compact=false}:{children:React.ReactNode;user?:User;compact?:boolean}){
  return <div className={`bs-shell${compact?' bs-shell-compact':''}`}><a href="#main-content" className="bs-skip">İçeriğe geç</a><SiteHeader user={user}/><main id="main-content" className="bs-main">{children}</main><SiteFooter dataMode={user?.data_mode}/></div>;
}

export function MethodTabs(){
  const [active,setActive]=useState('changes');
  const tabs=[['changes','İzlenen değişimler'],['sources','Veriler nereden geliyor'],['evidence','Önem ve kanıt gücü'],['data-states','Veri durumları'],['limits-of-use','Ne yapmaz'],['limits','Sınırlar']];
  return <nav aria-label="Yöntem bölümleri" className="bs-method-tabs">{tabs.map(([id,label])=><a key={id} className={active===id?'active':undefined} href={`#${id}`} onClick={()=>setActive(id)}>{label}</a>)}</nav>;
}
