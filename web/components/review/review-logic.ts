// Pure review-queue logic shared by the review page and the fund decision panel.
export type Decision={fund_code:string;fund_name?:string|null;packet_sha256:string;original_value:string|null;review_reason:string|null;reviewed_at:string|null;reviewer_email:string|null;ai_mode:string|null;decision_id:number|null;effective_value:string;decided_by:string;rationale_tr:string;validation_state:string|null;allowed_options:string[];stale_review_exists:boolean;has_current_review:boolean;evidence_ids:string[];team_proposal?:boolean};
export type ReviewAction='ACCEPT'|'OVERRIDE'|'REJECT';
export type ReviewResult={ok:true;message:string}|{ok:false;message:string};
export type ProposalSource='team'|'ai'|'synthetic'|'rules'|'none';
type Send=(path:string,body:unknown)=>Promise<Response>;

export const decisionLabels:Record<string,string>={MATERIAL:'İnceleme açısından önemli',NOT_MATERIAL:'Mevcut kanıta göre önemli görülmedi',DATA_ISSUE:'Veri sorunu',INSUFFICIENT_EVIDENCE:'Kanıt yetersiz',UNDECIDED:'Karar verilmedi'};
export const decisionOrder=['MATERIAL','DATA_ISSUE','INSUFFICIENT_EVIDENCE','NOT_MATERIAL','UNDECIDED'];
export function decisionLabel(value:string|null):string{return decisionLabels[value??'UNDECIDED']??'İnceleme bekliyor';}
export function decisionTone(value:string):'important'|'attention'|'neutral'{return value==='MATERIAL'?'important':value==='DATA_ISSUE'?'attention':'neutral';}

/** Stored provenance controls the label, including after a human review. */
export function proposalSource(decision:Pick<Decision,'decided_by'|'team_proposal'>&Partial<Pick<Decision,'ai_mode'|'decision_id'|'validation_state'>>):ProposalSource{
  if(decision.decided_by==='DETERMINISTIC')return 'rules';
  if(decision.ai_mode==='off')return decision.validation_state==='INVALID'?'none':'rules';
  if(decision.ai_mode==='mock')return 'synthetic';
  if(decision.team_proposal)return 'team';
  if(decision.ai_mode==='live'||decision.decided_by==='AI')return 'ai';
  return 'none';
}
export const proposalSourceOrder:ProposalSource[]=['team','ai','synthetic','rules','none'];
export const proposalSourceTitles:Record<ProposalSource,string>={team:'Ajan ekibinin önerileri',ai:'Yapay zekâ önerileri',synthetic:'Örnek test önerileri',rules:'Kurala dayalı sonuçlar',none:'Öneri bekleyen kayıtlar'};
export const proposalSourceDescriptions:Record<ProposalSource,string>={
  team:'Raportör, ekibin kaynaklara dayanan incelemesini bir öneriye dönüştürür. Nihai karar insan incelemesiyle kaydedilir.',
  ai:'Kaynaklara dayanan yapay zekâ önerilerinin ilk hali korunur. Etkin karar ve insan incelemesi ayrı gösterilir.',
  synthetic:'Bu kayıtlar örnek test verisiyle üretilmiştir.',
  rules:'Sabit hesaplamaların ve veri yeterliliği kontrollerinin sonuçlarıdır.',
  none:'Bu kayıtlar için henüz geçerli bir öneri bulunmuyor.'
};
export function proposalOriginLabel(decision:Parameters<typeof proposalSource>[0]):string{
  return {team:'Ajan ekibinin Raportör önerisi',ai:'Yapay zekâ önerisi',synthetic:'Örnek test önerisi',rules:'Kurala dayalı sonuç',none:'Henüz geçerli bir öneri yok'}[proposalSource(decision)];
}
export function reviewStateLabel(decision:Pick<Decision,'has_current_review'|'decision_id'|'validation_state'>):string{
  if(decision.has_current_review)return 'İnsan kararı kaydedildi';
  if(decision.decision_id===null)return 'Öneri bekleniyor';
  return decision.validation_state==='INVALID'?'İnsan kararı gerekiyor':'İnsan incelemesi bekliyor';
}

/** Who stands behind the decision shown on a card. */
export function proposerLabel(decision:Pick<Decision,'decided_by'|'team_proposal'>&Partial<Pick<Decision,'decision_id'|'validation_state'|'ai_mode'>>):string{
  if(decision.decided_by==='HUMAN')return 'İnsan incelemesi';
  const source=proposalSource(decision);
  if(source==='rules'||source==='synthetic')return proposalOriginLabel(decision);
  if(source==='none'&&decision.decision_id!=null&&decision.validation_state==='INVALID')return 'Geçerli öneri üretilemedi; insan kararı gerekiyor';
  // A proposal that failed validation never becomes the effective decision; a human decides.
  if(decision.decision_id!=null&&decision.validation_state==='INVALID')return decision.team_proposal?'Raportör önerisi doğrulamadan geçmedi; karar insanda':'Yapay zekâ önerisi doğrulamadan geçmedi; karar insanda';
  return proposalOriginLabel(decision);
}
/** The server accepts only a valid proposal; an invalid one can still be changed or rejected. */
export function canAccept(decision:Pick<Decision,'decision_id'|'validation_state'>):boolean{return decision.decision_id!==null&&decision.validation_state==='VALID';}
export function defaultOverride(decision:Pick<Decision,'allowed_options'|'original_value'|'effective_value'>):string{
  return decision.allowed_options.find(option=>option!==decision.original_value&&option!==decision.effective_value)??decision.allowed_options[0]??'';
}

export function validateReview(action:ReviewAction,overrideValue:string|null,reason:string,allowed:string[]):string|null{
  if(action==='OVERRIDE'&&(!overrideValue||!allowed.includes(overrideValue)))return 'Yeni kararı seçin.';
  if(action!=='ACCEPT'&&!reason.trim())return action==='OVERRIDE'?'Kararı neden değiştirdiğinizi yazın.':'Öneriyi neden reddettiğinizi yazın.';
  if(reason.length>1000)return 'Gerekçe en fazla 1000 karakter olabilir.';
  return null;
}
/** The exact body POST /decisions/{id}/reviews expects. */
export function reviewBody(action:ReviewAction,overrideValue:string|null,reason:string){
  return {action,override_value:action==='OVERRIDE'?overrideValue:null,reason:reason.trim()||null};
}
export function reviewErrorMessage(status:number,detail:unknown):string{
  if(detail==='REVIEW_REASON_REQUIRED')return 'Bu işlem için gerekçe gerekiyor.';
  if(detail==='REVIEW_NOT_ALLOWED')return 'Bu öneri bu işlemle incelenemiyor. Sayfayı yenileyip yeniden deneyin.';
  if(detail==='DECISION_OUTSIDE_SELECTED_DATE')return 'Bu öneri seçili analiz tarihine ait değil. Tarih seçimini kontrol edin.';
  if(status===401)return 'Oturumunuz sona ermiş. Yeniden giriş yapın.';
  if(status===403)return 'Bu işlem için yetkiniz doğrulanamadı. Sayfayı yenileyip yeniden deneyin.';
  return 'İnceleme kaydedilemedi. Biraz sonra yeniden deneyin.';
}
export function savedMessage(action:ReviewAction,overrideValue:string|null):string{
  if(action==='ACCEPT')return 'Öneri kabul edildi.';
  if(action==='OVERRIDE')return `Karar “${decisionLabel(overrideValue)}” olarak değiştirildi.`;
  return 'Öneri reddedildi; karar “Karar verilmedi” olarak görünür.';
}

export async function submitReview(send:Send,decision:Pick<Decision,'decision_id'|'allowed_options'>,action:ReviewAction,overrideValue:string|null,reason:string):Promise<ReviewResult>{
  if(decision.decision_id===null)return {ok:false,message:'Bu kanıt için incelenecek bir öneri yok.'};
  const invalid=validateReview(action,overrideValue,reason,decision.allowed_options);
  if(invalid)return {ok:false,message:invalid};
  let response:Response;
  try{response=await send(`/decisions/${decision.decision_id}/reviews`,reviewBody(action,overrideValue,reason));}
  catch{return {ok:false,message:'Sunucuya erişilemiyor. Bağlantınızı kontrol edip yeniden deneyin.'};}
  if(response.ok)return {ok:true,message:savedMessage(action,overrideValue)};
  let detail:unknown=null;
  try{detail=(await response.json())?.detail;}catch{detail=null;}
  return {ok:false,message:reviewErrorMessage(response.status,detail)};
}

export function reviewedAtTr(value:string|null):string{
  return value?new Intl.DateTimeFormat('tr-TR',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/Istanbul'}).format(new Date(value)):'Tarih kaydı yok';
}
