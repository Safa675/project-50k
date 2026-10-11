import {describe,expect,it,vi} from 'vitest';
import {canAccept,defaultOverride,proposerLabel,reviewBody,submitReview,validateReview} from '../components/review/review-logic';

const proposal={decision_id:42,allowed_options:['MATERIAL','DATA_ISSUE','INSUFFICIENT_EVIDENCE']};
describe('human review contract',()=>{
  it('allows accepting only a valid stored proposal',()=>{
    expect(canAccept({decision_id:42,validation_state:'VALID'})).toBe(true);
    expect(canAccept({decision_id:42,validation_state:'INVALID'})).toBe(false);
    expect(canAccept({decision_id:null,validation_state:'VALID'})).toBe(false);
  });
  it('requires a reason for change and rejection, and a permitted replacement',()=>{
    expect(validateReview('ACCEPT',null,'',proposal.allowed_options)).toBeNull();
    expect(validateReview('OVERRIDE','DATA_ISSUE','  ',proposal.allowed_options)).toContain('neden');
    expect(validateReview('REJECT',null,'\n',proposal.allowed_options)).toContain('neden');
    expect(validateReview('OVERRIDE','NOT_MATERIAL','Synthetic reason',proposal.allowed_options)).toContain('seçin');
    expect(validateReview('REJECT',null,'x'.repeat(1001),proposal.allowed_options)).toContain('1000');
  });
  it('sends the unchanged POST contract and accepts in one call without a reason',async()=>{
    const send=vi.fn(async()=>new Response('{}',{status:200}));
    expect(await submitReview(send,proposal,'ACCEPT',null,'')).toEqual({ok:true,message:'Öneri kabul edildi.'});
    expect(send).toHaveBeenCalledExactlyOnceWith('/decisions/42/reviews',{action:'ACCEPT',override_value:null,reason:null});
    expect(reviewBody('OVERRIDE','DATA_ISSUE',' Synthetic reason ')).toEqual({action:'OVERRIDE',override_value:'DATA_ISSUE',reason:'Synthetic reason'});
    expect(reviewBody('REJECT','MATERIAL',' Synthetic reason ')).toEqual({action:'REJECT',override_value:null,reason:'Synthetic reason'});
  });
  it('does not send an invalid review or a review without a proposal',async()=>{
    const send=vi.fn();
    expect((await submitReview(send,proposal,'REJECT',null,'')).ok).toBe(false);
    expect((await submitReview(send,proposal,'OVERRIDE','NOT_MATERIAL','Synthetic reason')).ok).toBe(false);
    expect((await submitReview(send,{...proposal,decision_id:null},'ACCEPT',null,'')).ok).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });
  it('shows server and network errors without claiming that a review was saved',async()=>{
    const expired=await submitReview(async()=>new Response('{}',{status:401}),proposal,'ACCEPT',null,'');
    expect(expired).toEqual({ok:false,message:'Oturumunuz sona ermiş. Yeniden giriş yapın.'});
    const dated=await submitReview(async()=>new Response(JSON.stringify({detail:'DECISION_OUTSIDE_SELECTED_DATE'}),{status:422}),proposal,'ACCEPT',null,'');
    expect(dated.ok).toBe(false);expect(dated.message).toContain('seçili analiz tarihine');
    const offline=await submitReview(async()=>{throw new Error('Synthetic network failure');},proposal,'ACCEPT',null,'');
    expect(offline.ok).toBe(false);expect(offline.message).toContain('Sunucuya erişilemiyor');
  });
  it('keeps the reporter, human reviewer and invalid proposal distinct',()=>{
    expect(proposerLabel({decided_by:'AI',team_proposal:true})).toBe('Ajan ekibinin Raportör önerisi');
    expect(proposerLabel({decided_by:'HUMAN',team_proposal:true})).toBe('İnsan incelemesi');
    expect(proposerLabel({decided_by:'UNDECIDED',decision_id:42,validation_state:'INVALID',team_proposal:true})).toContain('doğrulamadan geçmedi');
    expect(defaultOverride({...proposal,original_value:'MATERIAL',effective_value:'MATERIAL'})).toBe('DATA_ISSUE');
  });
});
