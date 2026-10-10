'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <section role="alert"><h1>Veri şu anda yüklenemiyor</h1><p>Bağlantıyı kontrol edip yeniden deneyin. Eksik veriler tamamlanmış gibi gösterilmez.</p><button onClick={reset}>Yeniden dene</button></section>;}
