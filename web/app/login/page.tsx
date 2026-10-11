'use client';
import {FormEvent,useState} from 'react';
import {post} from '@/lib/client';
import {ThemeToggle} from '@/components/DesignShell';
import styles from './login.module.css';
export default function Login() {
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError('');const form=new FormData(event.currentTarget);try{const challenge=await fetch('/api/p/auth/csrf',{cache:'no-store'});if(!challenge.ok)throw new Error();const {csrf_token}=await challenge.json();const response=await post('/auth/login',{email:form.get('email'),password:form.get('password')},csrf_token);if(response.ok){window.location.assign('/funds');return;}setError(response.status===429?'Çok sayıda giriş denemesi yapıldı. Daha sonra yeniden deneyin.':response.status===401?'E-posta veya parola doğru değil.':'Giriş şu anda tamamlanamıyor.');}catch{setError('Sunucuya erişilemiyor. Yeniden deneyin.');}finally{setBusy(false);}}
  return <main className={styles.page}>
    <div className={styles.topbar}><a href="/" className={styles.home}>← Ana sayfa</a><ThemeToggle/></div>
    <div className={styles.center}>
      <a className={styles.brand} href="/" aria-label="BlackSwan ana sayfa"><img src="/design/logo-auth.svg" alt="" width={56} height={56}/><span><span className={styles.brandLight}>Black</span><span className={styles.brandMedium}>Swan</span></span></a>
      <div className={styles.card}>
        <div className={styles.introduction}><h1>Çalışma alanınıza giriş yapın</h1><p>Fon ve hisse verilerine, kaynak kayıtlarına ve ekip incelemelerine hesabınızla erişin.</p></div>
        <form className={styles.form} onSubmit={submit} aria-busy={busy}>
          <label>E-posta<input type="email" name="email" autoComplete="username" required maxLength={320}/></label>
          <label>Parola<input type="password" name="password" autoComplete="current-password" required maxLength={1024}/></label>
          <button className={styles.submit} disabled={busy}>{busy?'Giriş yapılıyor…':'Giriş yap'}</button>
          {error&&<p className={styles.error} role="alert">{error}</p>}
        </form>
        <p className={styles.access}>Veriler ve inceleme kayıtları yalnızca oturum açmış kullanıcılar tarafından görüntülenir.</p>
      </div>
      <p className={styles.limit}>Yatırım tavsiyesi değildir.</p>
    </div>
  </main>;
}
