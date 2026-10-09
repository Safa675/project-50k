'use client';
import {useTranslations} from 'next-intl';
import Link from 'next/link';
export default function Shell({children,synthetic=false,onHomeNavigate}:{children:React.ReactNode,synthetic?:boolean,onHomeNavigate?:()=>void}){
 const t=useTranslations('app');
 return <><header className="site-header"><div className="header-inner"><Link className="brand" href={synthetic?'/preview':'/'} onNavigate={onHomeNavigate}>Fon araştırması <small>Project 50K</small></Link><span className="archive-label">{synthetic?'Örnek verilerle tasarım önizlemesi':t('archive')}</span></div></header><main>{children}<footer><span>Kaynak sürümlerinin geçmişte erişilebilir olduğu doğrulanmadı.</span><span>Fon seçimi: Ekim 2026 yatırımcı sıralaması · Kategoriler: mevcut anlık görüntü</span><span>Veri hakları incelenmedi · Üretim kararları değerlendirme dışı</span></footer></main></>;
}
