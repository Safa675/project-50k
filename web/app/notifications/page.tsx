import {requireUser,serverApi} from '@/lib/auth';
import {DesignShell} from '@/components/DesignShell';
import {NotificationData,NotificationsContent} from '@/components/WatchlistViews';
export const dynamic='force-dynamic';
export default async function Page({searchParams}:{searchParams:Promise<{unread?:string;offset?:string}>}){
  const user=await requireUser(),params=await searchParams,unreadOnly=params.unread==='1';
  const parsed=Number(params.offset??0),offset=Number.isInteger(parsed)&&parsed>=0?Math.min(800,parsed):0;
  const response=await serverApi(`/notifications?unread_only=${unreadOnly}&offset=${offset}`);
  if(!response.ok)return <DesignShell user={user}><div className="watch-page"><h1>Bildirimler</h1><p role="alert">Bildirimler alınamadı. Sayfayı yenileyip tekrar deneyin.</p></div></DesignShell>;
  return <DesignShell user={user}><NotificationsContent data={await response.json() as NotificationData} unreadOnly={unreadOnly}/></DesignShell>;
}
