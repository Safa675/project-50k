'use client';
import {useState} from 'react';
import {post} from '@/lib/client';
import {useReady} from '@/lib/use-ready';
export default function SessionActions() {
  const [error,setError] = useState('');
  const [busy,setBusy]=useState(false),ready=useReady();
  return <div><button type="button" disabled={!ready||busy} onClick={async()=>{setBusy(true);setError('');try{const response=await post('/auth/logout');if(response.ok)window.location.assign('/login');else setError('Oturum kapatılamadı.');}catch{setError('Bağlantı kurulamadı. Yeniden deneyin.');}finally{setBusy(false);}}}>Çıkış yap</button>{error&&<p role="alert">{error}</p>}</div>;
}
