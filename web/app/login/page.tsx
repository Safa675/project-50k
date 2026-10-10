'use client';
import {FormEvent,useState} from 'react';
import {post} from '@/lib/client';
export default function Login() {
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError('');const form=new FormData(event.currentTarget);try{const challenge=await fetch('/api/p/auth/csrf',{cache:'no-store'});if(!challenge.ok)throw new Error();const {csrf_token}=await challenge.json();const response=await post('/auth/login',{email:form.get('email'),password:form.get('password')},csrf_token);if(response.ok){window.location.assign('/funds');return;}setError(response.status===429?'Çok sayıda giriş denemesi yapıldı. Daha sonra yeniden deneyin.':response.status===401?'E-posta veya parola doğru değil.':'Giriş şu anda tamamlanamıyor.');}catch{setError('Sunucuya erişilemiyor. Yeniden deneyin.');}finally{setBusy(false);}}
  return <main className="login"><a className="wordmark" href="/">BlackSwan</a><h1>Ekibin çalışma alanı</h1><p>Fon verileri ve inceleme kayıtları yalnızca oturum açmış kullanıcılar tarafından görüntülenir.</p><form onSubmit={submit}><label>E-posta<input type="email" name="email" autoComplete="username" required maxLength={320}/></label><label>Parola<input type="password" name="password" autoComplete="current-password" required maxLength={1024}/></label><button disabled={busy}>{busy?'Giriş yapılıyor…':'Giriş yap'}</button>{error&&<p role="alert">{error}</p>}</form><p className="muted">Yatırım tavsiyesi değildir</p></main>;
}
