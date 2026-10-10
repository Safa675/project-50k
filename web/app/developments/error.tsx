'use client';
export default function EvidenceError({reset}:{reset:()=>void}){return <section className="evidence-detail"><h1>Kanıta erişilemiyor</h1><p>Kaynak yanıtı şu anda alınamadı.</p><button onClick={reset}>Yeniden dene</button></section>;}
