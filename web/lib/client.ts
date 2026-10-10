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
