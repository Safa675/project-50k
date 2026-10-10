export function csrfCookie(): string {
  return decodeURIComponent(document.cookie.split('; ').find(value => value.startsWith('p50k_csrf='))?.slice(10) ?? '');
}
export async function post(path: string, body?: unknown, csrf?: string) {
  return fetch(`/api/p${path}`, {method: 'POST', headers: {'Content-Type':'application/json','X-CSRF-Token':csrf ?? csrfCookie()},
    body: JSON.stringify(body ?? {}), cache:'no-store'});
}
export function decimal(value: string|null): string {return value === null ? 'Veri yok' : value.replace('.', ',');}
export function dateTr(value: string|null): string {return value ? new Intl.DateTimeFormat('tr-TR',{dateStyle:'medium',timeZone:'Europe/Istanbul'}).format(new Date(value.includes('T')?value:`${value}T12:00:00+03:00`)) : 'Tarih bilinmiyor';}
export const stateTr: Record<string,string> = {TRIGGERED:'İnceleme bulgusu',NOT_TRIGGERED:'Eşik aşılmadı',ABSTAINED:'Yeterli kanıt yok'};
const reasons:Record<string,string>={CATEGORY_MISSING:'Fonun kategorisi bilinmiyor.',NO_CATEGORY_THRESHOLD:'Bu kategori için kalibre edilmiş eşik yok.',CURRENT_INPUT_OR_HISTORY_UNAVAILABLE:'Güncel gözlem, benzer fon verisi veya geçmiş uzunluğu hesaplamaya yetmiyor.',THRESHOLD_EXCEEDED:'Detektörün sabit eşik sınırı aşıldı.',WITHIN_THRESHOLD:'Hesaplanan değer sabit eşik sınırını aşmadı.',OBSERVED_HISTORY_ATTRIBUTE:'İlk görülen pozitif fiyattan bu yana geçen gün sayısı; gerçek kuruluş tarihini göstermez.',NO_POSITIVE_HISTORY:'Uygun zamanlı pozitif fiyat geçmişi yok.',STALE_DAILY_PRICE:'Arşivdeki son fiyat beklenen yayımlanma aralığının gerisinde; resmî tatil takvimi doğrulanmadı.',WITHIN_PUBLISHED_CADENCE:'Son gözlem yayımlanma aralığı içinde.',NO_ADMISSIBLE_PRICE_HISTORY:'Bu gösterge için uygun zamanlı fiyat geçmişi bulunmuyor.',LATEST_NAV_MISSING:'Son gözlemde birim fiyat eksik veya çelişkili.',LATEST_NAV_AVAILABLE:'Son gözlemde birim fiyat mevcut.',CONFIRMED_SPK_EVENT:'Kapsam içindeki resmî olay insan tarafından doğrulandı.',EVENT_UNCONFIRMED_OR_UNDATED:'Olayın kimliği veya kesin yayım zamanı henüz doğrulanmış değil.',SOURCE_SCOPE_LIMITED:'İncelenen kaynak kapsamı yalnızca SPK 2026/61; kayıt bulunmaması olay olmadığı anlamına gelmez.'};
export function reasonTr(value:string):string{return reasons[value]??'Bu gösterge için kaynak sınırlamaları incelenmelidir.';}
