/** Presentation calculations use only the unchanged baseline evaluation response. */
type CoverageCounts={scanned:number;listed_not_assessable:number;other_not_assessable:number};
type CaseFund={fund_code:string;name:string;detectors:string[];outcomes:{price:string};href:string};
export const caseFundCodes=['THF','TP2','PRY','PNU','DFI','DOH','KHA','TLY'] as const;
export type CaseOutcome='caught'|'missed'|'not_assessable'|'missing';

export function assessedCoverage(counts:CoverageCounts):{scanned:number;assessed:number|null;notAssessable:number|null;percent:string|null}{
  const values=[counts.scanned,counts.listed_not_assessable,counts.other_not_assessable];
  if(values.some(value=>!Number.isInteger(value)||value<0))return {scanned:counts.scanned,assessed:null,notAssessable:null,percent:null};
  const notAssessable=counts.listed_not_assessable+counts.other_not_assessable;
  if(notAssessable>counts.scanned)return {scanned:counts.scanned,assessed:null,notAssessable:null,percent:null};
  const assessed=counts.scanned-notAssessable;
  return {scanned:counts.scanned,assessed,notAssessable,percent:counts.scanned>0?(100*assessed/counts.scanned).toFixed(1):null};
}

export function caseFundBreakdown(funds:CaseFund[]){
  const rows=caseFundCodes.map(code=>{
    const fund=funds.find(item=>item.fund_code===code),price=fund?.outcomes.price;
    const outcome:CaseOutcome=price==='caught'?'caught':price==='missed'?'missed':price==='listed_not_assessable'||price==='other_not_assessable'?'not_assessable':'missing';
    return {code,fund:fund??null,outcome,d1Flagged:fund?fund.detectors.includes('D1'):null};
  });
  return {rows,total:caseFundCodes.length,available:rows.filter(row=>row.fund!==null).length,
    d1Flagged:rows.filter(row=>row.d1Flagged===true).length,caught:rows.filter(row=>row.outcome==='caught').length,
    missed:rows.filter(row=>row.outcome==='missed').length,notAssessable:rows.filter(row=>row.outcome==='not_assessable').length,
    missing:rows.filter(row=>row.outcome==='missing').length};
}
