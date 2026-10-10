import {dateTr} from '@/lib/client';
import {methodFor} from '@/lib/method-explanations';

export default function MethodExplanation({code,effectiveDate,asOf}:{code:string;effectiveDate?:string|null;asOf?:string|null}){
  const method=methodFor(code);if(!method)return null;
  return <details className="method-explanation"><summary>Bu sonuca nasıl ulaştık?</summary><dl><div><dt>Hangi bilgi kullanıldı?</dt><dd>{method.inputs}</dd></div>{effectiveDate&&<div><dt>Bu kaydın tarihi</dt><dd>{dateTr(effectiveDate)}</dd></div>}{asOf&&asOf!==effectiveDate&&<div><dt>İncelenen son veri tarihi</dt><dd>{dateTr(asOf)}</dd></div>}<div><dt>Nasıl karşılaştırıldı?</dt><dd>{method.comparison}</dd></div><div><dt>Ne anlama gelir?</dt><dd>{method.meaning}</dd></div><div><dt>Neyi söylemez?</dt><dd>{method.limits}</dd></div></dl><a href="/method#changes">Tüm inceleme yöntemlerini gör</a></details>;
}
