export type FundPoint = {
  effective_date: string;
  nav: string | null;
  ambiguous_revision: boolean;
  source_id?: string;
  source_sha256?: string;
  available_at?: string | null;
  published_at?: string | null;
  availability_rule?: string;
};

export type FundSignal = {
  fund_code: string;
  detector_id: string;
  state: string;
  reason: string;
  value: string | null;
  threshold: string | null;
  effective_date: string | null;
  available_at: string | null;
  is_attribute: boolean;
  evidence_id: string;
  source_references: {source_id: string; source_sha256: string; available_at: string | null}[];
};

export const detectorNames: Record<string, string> = {
  D1: 'Benzer fonlara göre fiyat farkı',
  D2: 'Benzer fonlarla farkın değişimi',
  D3: 'Günlük fiyat hareketlerinin benzerliği',
  D4: 'Benzer fonlarla birlikte hareket',
  D5: 'Eldeki fiyat geçmişi',
  'AN-DQ-001': 'Fiyatın güncelliği',
  'AN-DQ-002': 'Birim fiyatın erişilebilirliği',
  'AN-FND-005': 'Düzenleyici kayıt',
};

export function signalName(code:string):string{return detectorNames[code]??'Fon incelemesi';}
export function sourceName(code:string|null|undefined):string{
  const name=(code??'').toLocaleLowerCase('en-US');
  if(name.includes('tefas'))return 'TEFAS';
  if(name.includes('kap'))return 'KAP';
  if(name.includes('spk'))return 'Sermaye Piyasası Kurulu';
  if(name.includes('forinvest'))return 'ForInvest';
  return 'Yayımlanmış kaynak';
}
export function latestKnownNav(points:FundPoint[]):FundPoint|undefined{return [...points].reverse().find(point=>knownNav(point)!==null);}
export function friendlyEvidenceText(text:string):string{
  let result=text.replace(/\b(D[1-5]|AN-DQ-\d{3}|AN-FND-\d{3}) \[değer: ([^;]+); eşik: ([^;]+); ([^\]]+)\]/g,(_,code:string,value:string,threshold:string,state:string)=>{
    const parts=[state==='kanıt yetersiz'?'bilgi yetersiz':state==='eşik aşıldı'?'inceleme gerekiyor':'belirgin değişim görülmedi'];
    return `${signalName(code)} (${parts.join('; ')})`;
  });
  for(const [code,name] of Object.entries(detectorNames))result=result.replace(new RegExp(`\\b${code}\\b`,'g'),name);
  return result;
}

export function sourceTime(value: string | null | undefined): string {
  return value ? new Intl.DateTimeFormat('tr-TR', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'Europe/Istanbul'}).format(new Date(value)) : 'Zaman bilinmiyor';
}

export function knownNav(point: FundPoint): number | null {
  if (point.nav === null || point.ambiguous_revision) return null;
  const value = Number(point.nav);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function fundWindow(points: FundPoint[], days: number | null): FundPoint[] {
  if (!points.length || days === null) return points;
  const end = Date.parse(points[points.length - 1].effective_date);
  const start = end - (days - 1) * 86400000;
  return points.filter(point => Date.parse(point.effective_date) >= start);
}

export function fundSeries(points: FundPoint[]) {
  const values = points.map(knownNav);
  const known = values.filter((value): value is number => value !== null);
  if (!known.length) return {segments: [], low: null, high: null, coordinates: []};
  const low = Math.min(...known), high = Math.max(...known);
  const start = Date.parse(points[0].effective_date);
  const span = Math.max(1, Date.parse(points[points.length - 1].effective_date) - start);
  const coordinates = points.map((point, index) => ({
    index,
    x: 12 + (Date.parse(point.effective_date) - start) * 780 / span,
    y: values[index] === null ? null : high === low ? 148 : 270 - (values[index]! - low) / (high - low) * 244,
  }));
  const segments: {index: number; x: number; y: number}[][] = [];
  let segment: {index: number; x: number; y: number}[] = [];
  for (const point of coordinates) {
    if (point.y === null) {
      if (segment.length) segments.push(segment);
      segment = [];
    } else segment.push({...point, y: point.y});
  }
  if (segment.length) segments.push(segment);
  return {segments, low, high, coordinates};
}
