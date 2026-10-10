import Link from 'next/link';
import {serverApi,User} from '@/lib/auth';
import {DesignShell} from '@/components/DesignShell';
import {WatchData,WatchlistContent} from '@/components/WatchlistViews';
import '@/components/watchlist.css';
export const dynamic='force-dynamic';

export default async function Page(){
  const me=await serverApi('/auth/me');
  if(me.status===401)return <DesignShell><div className="watch-signed-out"><section className="watch-login-call"><span className="watch-empty-icon"><img src="/figma-watchlist/bookmark-large.svg" alt=""/></span><div><h1>Takip listesi için giriş gerekir</h1><p>Takip listesi, izlenen fonları tek yerde toplar. Bu fonlardaki inceleme bulguları burada ve bildirimlerde görünür.</p></div><Link href="/login" className="watch-primary"><img src="/figma-watchlist/login.svg" alt=""/>Giriş yap</Link><p className="watch-small">Fon miktarı girilmesi gerekmez. Fonlar istenildiği zaman listeden çıkarılabilir.</p></section><div className="watch-features"><section><img src="/figma-watchlist/bookmark.svg" alt=""/><h2>Fonlar tek yerde</h2><p>Fonlar, adı ya da TEFAS koduyla aranır ve takip listesine eklenir.</p></section><section><img src="/figma-watchlist/bell.svg" alt=""/><h2>Bulgularda bildirim</h2><p>Tamamlanan analizlerdeki inceleme bulguları uygulama içi bildirimlerde görünür.</p></section><section><img src="/figma-watchlist/source.svg" alt=""/><h2>Kaynağıyla birlikte</h2><p>Her bulgunun kaynak kaydı ve kullanılabilirlik zamanı kanıt ekranında yer alır.</p></section></div></div></DesignShell>;
  if(!me.ok)throw new Error('Oturum doğrulanamadı.');
  const session=await me.json(),user={...session.user,data_mode:session.data_mode} as User;
  const response=await serverApi('/watchlist');
  if(!response.ok)return <DesignShell user={user}><div className="watch-page"><h1>Takip listem</h1><p role="alert">Takip listesi alınamadı. Sayfayı yenileyip tekrar deneyin.</p></div></DesignShell>;
  return <DesignShell user={user}><WatchlistContent data={await response.json() as WatchData}/></DesignShell>;
}
