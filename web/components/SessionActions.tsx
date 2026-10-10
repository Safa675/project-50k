'use client';
import {useState} from 'react';
import {post} from '@/lib/client';
export default function SessionActions() {
  const [error,setError] = useState('');
  return <div><button type="button" onClick={async()=>{const response=await post('/auth/logout'); if(response.ok)window.location.assign('/login'); else setError('Oturum kapatılamadı.');}}>Çıkış yap</button>{error&&<p role="alert">{error}</p>}</div>;
}
