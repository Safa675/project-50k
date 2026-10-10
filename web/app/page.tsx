import Link from 'next/link';
import {DesignShell,SearchField} from '@/components/DesignShell';
import {optionalUser} from '@/lib/optional-user';
import RealEvidenceExample from '@/components/RealEvidenceExample';

export const dynamic='force-dynamic';

export default async function Home(){
  const user=await optionalUser();
  return <DesignShell user={user}><div className="bs-landing" data-design-node="25:456"><section className="bs-hero" aria-labelledby="title"><div className="bs-hero-copy"><h1 id="title">Kara kuğu öngörülemez.<strong>Ama izleri görülebilir.</strong></h1><p>Bankalar ve finansal kurumlar için kanıt verisi ve API çalışma alanı. Fon bulgularını ve BIST 30 günlük fiyatlarını kaynaklarıyla inceleyin.</p></div><SearchField large/></section>
    <section aria-labelledby="example-title"><h2 id="example-title" className="bs-section-title">Bir gelişme nasıl görünür?</h2><p className="bs-section-intro">İnceleme tarihini seçerek fonun arşiv kaynaklarını ve hesaplanan karşılaştırmaları görün. Sonuçların dayandığı veri tarihleri her kaydın yanında yer alır.</p><div className="bs-example"><RealEvidenceExample/></div></section>
    <section aria-labelledby="how-title"><h2 id="how-title" className="bs-section-title">Nasıl çalışır</h2><div className="bs-how-grid"><article className="bs-how-card"><img src="/design/bell-plus.svg" alt=""/><div><h3>Fon takibe alınır</h3><p>Takip listesine fonlar eklenir; fon miktarı girilmesi gerekmez. BIST 30 günlük fiyatları ve kaynakları Hisseler bölümünde incelenir.</p></div></article><article className="bs-how-card"><img src="/design/activity-large.svg" alt=""/><div><h3>Gelişme görünür</h3><p>Yayımlanmış veriler sabit kurallarla değerlendirilir. Hesaplanan değişimler ve eksik kanıtlar birlikte gösterilir.</p></div></article><article className="bs-how-card"><img src="/design/file-search.svg" alt=""/><div><h3>Kaynak incelenir</h3><p>Her gelişmenin yanında kaynağı, erişilebilirlik zamanı ve henüz bilinmeyenler yazar.</p></div></article></div></section>
    <section><div className="bs-limits-card"><div><h2 className="bs-section-title">Ne yapmaz</h2><p>Yatırım kararı kullanıcıya aittir. BlackSwan değişimi ve kaynağını gösterir.</p></div><ul className="bs-limits-list"><li><img src="/design/slash-circle.svg" alt=""/>Al, sat ya da tut tavsiyesi vermez.</li><li><img src="/design/slash-circle.svg" alt=""/>Hiçbir fonu “güvenli” ya da “riskli” olarak nitelendirmez.</li><li><img src="/design/slash-circle.svg" alt=""/>Geleceği ya da bir fonun ne olacağını tahmin etmez.</li></ul></div></section>
    <section className="bs-landing-cta"><h2 className="bs-section-title">Kanıtları incelemeye başla</h2><Link href={user?'/funds':'/login'} className="bs-button"><img src="/design/login.svg" alt=""/>{user?'Çalışma alanını aç':'Giriş yap'}</Link></section></div></DesignShell>;
}
