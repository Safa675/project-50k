import type {Fund} from './research-contract';
export type FindingFilter='all'|'two'|'one'|'unavailable'|'none';
export function matchesFund(fund:Fund,query:string,category:string,finding:FindingFilter){
  const needle=query.trim().toLocaleLowerCase('tr-TR');
  const name=fund.name.toLocaleLowerCase('tr-TR');
  const codeMatches=fund.code.toUpperCase().includes(query.trim().toUpperCase());
  if(needle && !codeMatches && !name.includes(needle))return false;
  if(category && fund.category!==category)return false;
  if(finding==='two')return fund.eligible_crossings===2;
  if(finding==='one')return fund.eligible_crossings===1;
  if(finding==='unavailable')return fund.assessment!=='FULL';
  if(finding==='none')return fund.assessment==='FULL'&&fund.eligible_crossings===0;
  return true;
}
export function percent(value:string|null,digits=2){return value===null?'—':new Intl.NumberFormat('tr-TR',{style:'percent',minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Number(value));}
export function amount(value:string|null,digits=2){return value===null?'—':new Intl.NumberFormat('tr-TR',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(Number(value));}
export function date(value:string|null){if(!value)return 'Bilinmiyor';return new Intl.DateTimeFormat('tr-TR',{timeZone:'Europe/Istanbul',...(value.length===7?{month:'long' as const,year:'numeric' as const}:{dateStyle:'medium' as const}),...(value.includes('T')?{timeStyle:'short' as const}:{})}).format(new Date(value.includes('T')?value:`${value.length===7?value+'-01':value}T12:00:00+03:00`));}
export function screenLabel(finding:Fund['d1']|Fund['flow']){
  if(finding.arithmetic_status==='UNAVAILABLE')return 'Veri yetersiz';
  if(finding.freshness==='STALE')return 'Güncel gözlem eksik';
  if(finding.research_screen==='CROSSING')return 'Eşik aşımı';
  if(finding.research_screen==='NO_CROSSING')return 'Eşik aşımı yok';
  return 'Değerlendirilemiyor';
}
export function flowLabel(fund:Fund){if(fund.flow.arithmetic_status==='UNAVAILABLE')return 'Veri yetersiz';if(fund.flow.research_screen==='CROSSING')return fund.flow.direction==='OUTFLOW_ESTIMATE'?'Çıkış tahmini':'Giriş tahmini';return screenLabel(fund.flow);}
export function assessmentLabel(fund:Fund){return fund.assessment==='UNAVAILABLE'?'Değerlendirilemiyor':fund.assessment==='PARTIAL'?'Eksik değerlendirme':'İki hesap mevcut';}
export function concentrationLabel(holding:Fund['concentration']) {return !holding ? 'Bu pakette hesaplanmadı' : holding.status === 'UNAVAILABLE' ? 'Hesaplanamadı' : holding.status === 'PARTIAL' ? 'Kısmi portföy' : 'Kıymetler hesaplandı';}
export function percentagePoints(value:string|null) {return value === null ? '—' : new Intl.NumberFormat('tr-TR', {signDisplay:'exceptZero',minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value)*100)+' yüzde puan';}
export const REASON_LABELS:Record<string,string>={MISSING_CATEGORY:'Kategori bilgisi eksik.',MISSING_CALIBRATION:'Kategori eşiği mevcut değil.',INSUFFICIENT_OBSERVATIONS:'Yeterli geçerli fiyat gözlemi yok.',INSUFFICIENT_PEERS:'Yeterli benzer fon yok.',MISSING_MONTHLY_PAIR:'Temmuz ve ağustos rapor çifti eksik.',MISSING_PUBLICATION_TIME:'Yayın zamanı bilinmiyor.',DUPLICATE_REPORT:'Aynı dönem için birden fazla uygun rapor var.',INCOMPATIBLE_UNITS:'Rapor birimleri karşılaştırılamıyor.',UNSUPPORTED_ACTION:'Karşılaştırmayı etkileyen bir işlem var.',STALE_D1:'16 Eylül için geçerli son gözlem eksik.'};
const FIELD_LABELS:Record<string,string>={currency:'Para birimi',assets_unit:'Toplam değer birimi',nav_unit:'Pay fiyatı birimi',fund_scope:'Fon kapsamı',share_class:'Pay sınıfı',valuation_basis:'Değerleme yöntemi',asset_basis:'Toplam değer tanımı',nav_basis:'Pay fiyatı tanımı',valuation_timezone:'Değerleme saat dilimi',distribution_status:'Dağıtım bilgisi',unit_change_status:'Pay değişimi',merger_status:'Birleşme bilgisi',previous_assets:'Temmuz toplam değeri',current_assets:'Ağustos toplam değeri',previous_nav:'Temmuz pay fiyatı',current_nav:'Ağustos pay fiyatı'};
const BACKEND_REASONS:Record<string,string>={kap_series_missing:'Aylık KAP serisi mevcut değil.',kap_series_invalid:'KAP serisi okunamadı.',price_source_missing:'Fiyat dosyası mevcut değil.',price_source_invalid:'Fiyat dosyası okunamadı.',price_row_invalid:'Fiyat kaydının biçimi geçersiz.',price_date_invalid:'Fiyat kaydının tarihi geçersiz.',duplicate_price_date:'Aynı tarih için birden fazla fiyat var.',stored_category_calibration_missing:'Bu kategori için kayıtlı eşik yok.',current_category_missing:'Kategori bilgisi mevcut değil.',fewer_than_10_category_peers:'En az 10 uygun benzer fon bulunamadı.',fewer_than_50_usable_excess_observations:'En az 50 geçerli getiri farkı gözlemi bulunamadı.',final_contributing_observation_before_cutoff:'Son geçerli gözlem 16 Eylül değil.',no_common_valid_baseline_with_10_peers:'En az 10 benzer fonla ortak geçerli başlangıç bulunamadı.',historical_availability_unknown:'Bu arşiv sürümünün geçmişte erişilebilirliği bilinmiyor.',baseline_unverified:'Akış için üretim karşılaştırma temeli doğrulanmadı.',endpoint_estimate_not_reported_cash:'Bu uç değer hesabı, bildirilen yatırımcı nakdi değildir.',peer_category_membership_from_current_snapshot:'Benzer fonların kategorileri mevcut anlık görüntüden alınmıştır.'};
export function reason(value:string):string{
 if(REASON_LABELS[value])return REASON_LABELS[value];if(BACKEND_REASONS[value])return BACKEND_REASONS[value];
 const monthly=/^(2026-07|2026-08)_(.*)$/.exec(value);if(monthly){const month=monthly[1]==='2026-07'?'Temmuz':'Ağustos';const labels:Record<string,string>={publication_missing_or_invalid:'raporunun yayın zamanı eksik veya geçersiz.',eligible_monthly_endpoint_missing:'için uygun aylık rapor bulunamadı.',duplicate_eligible_monthly_endpoint:'için birden fazla uygun aylık rapor var.'};return `${month} ${labels[monthly[2]]??'raporunun uygunluğu doğrulanamadı.'}`;}
 for(const [field,label] of Object.entries(FIELD_LABELS)){if(value===field+'_mismatch'||value===field+'_incompatible')return `${label} dönemler arasında karşılaştırılamıyor.`;if(value===field+'_unknown_common_report_field_assumption')return `${label} doğrulanmadı; dönemlerin aynı rapor kapsamını kullandığı varsayılıyor.`;if(value===field+'_unknown')return `${label} doğrulanmadı.`;if(value===field+'_missing')return `${label} mevcut değil.`;if(value===field+'_nonfinite'||value===field+'_requires_decimal'||value===field+'_invalid_sign')return `${label} hesap için geçerli değil.`;}
 if(value==='assets_nav_units_incompatible')return 'Toplam değer ve pay fiyatının birimleri uyumlu değil.';
 if(value.toLowerCase().includes('timezone')||value.toLowerCase().includes('istanbul'))return 'Saat dilimi kaydı eksik olduğunda KAP yayın saati İstanbul saati kabul edilmiştir.';
 return 'Bu verinin uygunluğu doğrulanamadı; hesap sınırlı olabilir.';
}
export function reportedPdfPeriod(fileName: string): string | null {
 return /^(\d{4}-(?:0[1-9]|1[0-2]))(?:\D|$)/.exec(fileName)?.[1] ?? null;
}
export function sourceTitle(source:{kind:string,fund_code:string|null,file_name:string}){
 const titles:Record<string,string>={PRICE:'Günlük fon fiyatları',KAP_SERIES:'KAP aylık sayısal serisi',KAP_PDF:'Orijinal KAP raporu',SNAPSHOT:'Fon kimliği ve kategori kaydı',CALIBRATION:'Kayıtlı kategori eşiği',UNIVERSE:'Seçili 100 fon listesi',PROTOCOL:'Sabit araştırma protokolü',CODE:'Hesaplama kodu'};
 const prefix=reportedPdfPeriod(source.file_name);
 if(source.kind==='KAP_SERIES'){titles.KAP_SERIES=source.file_name==='kap_report_list.json'||source.file_name.startsWith('kap_portfolio_reports_')?'KAP bildirim listesi':'PDF’den çıkarılan aylık veriler';}
 const period=source.kind==='KAP_PDF'&&prefix?` · ${date(prefix)}`:'';
 return `${source.fund_code?source.fund_code+' · ':''}${titles[source.kind]??'Araştırma kaynağı'}${period}`;
}
