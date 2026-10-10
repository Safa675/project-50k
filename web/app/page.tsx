import {apiOrigin} from '@/lib/proxy';

export const dynamic = 'force-dynamic';

async function databaseAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${apiOrigin()}/health/ready`, {cache: 'no-store', signal: AbortSignal.timeout(5000)});
    if (!response.ok) return false;
    const result: unknown = await response.json();
    return typeof result === 'object' && result !== null && 'database' in result && result.database === 'available';
  } catch {return false;}
}

export default async function Home() {
  const available = await databaseAvailable();
  return <main>
    <header><span className="wordmark">BlackSwan</span><span className="domain">Türkiye yatırım fonları</span></header>
    <section aria-labelledby="title">
      <p className="eyebrow">KANITA DAYALI İNCELEME</p>
      <h1 id="title">Veriyi görün.<br/>Kararı sorgulayın.</h1>
      <p className="intro">BlackSwan, yatırım fonlarının yayımlanmış verilerini ve düzenleyici olaylarını incelemek için geliştiriliyor. Fon verilerine erişim oturum açmayı gerektirir.</p>
      <div className="service-status" role="status"><span className={available ? 'dot available' : 'dot'}/><span>{available ? 'Veritabanı bağlantısı hazır' : 'Veritabanına şu anda erişilemiyor'}</span></div>
      <p className="access-state">Bu kurulumda fon inceleme erişimi henüz etkin değil.</p>
    </section>
    <footer><p>Geliştirme sonucu · Veri hakları incelenmedi · Yatırım tavsiyesi değildir</p></footer>
  </main>;
}
