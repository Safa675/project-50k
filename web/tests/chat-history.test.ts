import {describe,it,expect} from 'vitest';
import {chatAssetQuery,parseChatHistory,parseChatThreads,shouldSendOnEnter} from '../lib/chat-history';

const thread='00000000-0000-4000-8000-000000000001';
const common={fund_code:'THF',analysis_scope_key:'asof:2026-09-12'};
const message={role:'assistant',content:'Synthetic persisted answer',message_id:'1',created_at:'2026-10-10T12:00:00Z',status:'VALID',evidence_ids:['ev:synthetic'],evidence_labels:{'ev:synthetic':'Synthetic source'}};
describe('persisted chat boundaries',()=>{
  it('accepts only the requested asset, thread and analysis date',()=>{
    const history={...common,thread_id:thread,items:[message]};
    expect(parseChatHistory(history,'THF',thread,common.analysis_scope_key)).toEqual([message]);
    for(const value of [{...history,fund_code:'TP2'},{...history,analysis_scope_key:'live'},{...history,thread_id:'00000000-0000-4000-8000-000000000002'}])expect(()=>parseChatHistory(value,'THF',thread,common.analysis_scope_key)).toThrow();
  });
  it('rejects unvalidated assistant history and overlong transcripts',()=>{
    for(const items of [[{...message,status:'FAILED'}],Array.from({length:61},()=>message),[{...message,evidence_labels:{unknown:'Synthetic'}}]])expect(()=>parseChatHistory({...common,thread_id:thread,items},'THF',thread,common.analysis_scope_key)).toThrow();
  });
  it('accepts saved owner thread metadata and bounds selector size',()=>{
    const item={thread_id:thread,title:'Synthetic question',created_at:'2026-10-10T12:00:00Z',last_message_at:'2026-10-10T12:00:01Z',message_count:2};
    expect(parseChatThreads({...common,items:[item]},'THF',common.analysis_scope_key).items).toEqual([item]);
    expect(()=>parseChatThreads({...common,items:Array.from({length:21},()=>item)},'THF')).toThrow();
  });
  it('keeps the Raportör general conversation apart from fund conversations',()=>{
    const item={thread_id:thread,title:'Synthetic general question',created_at:'2026-10-10T12:00:00Z',last_message_at:null,message_count:2};
    const general={fund_code:null,analysis_scope_key:'live',items:[item]};
    expect(parseChatThreads(general,null,'live').items).toEqual([item]);
    expect(()=>parseChatThreads(general,'THF','live')).toThrow();
    expect(()=>parseChatThreads({...general,fund_code:'THF'},null,'live')).toThrow();
    expect(parseChatHistory({fund_code:null,analysis_scope_key:'live',thread_id:thread,items:[message]},null,thread,'live')).toEqual([message]);
    expect(chatAssetQuery(null)).toBe('');
    expect(chatAssetQuery('THF')).toBe('fund_code=THF');
  });
  it('sends Enter, preserves Shift+Enter and never submits during IME composition',()=>{
    expect(shouldSendOnEnter({key:'Enter',shiftKey:false})).toBe(true);
    expect(shouldSendOnEnter({key:'Enter',shiftKey:true})).toBe(false);
    expect(shouldSendOnEnter({key:'Enter',shiftKey:false,isComposing:true})).toBe(false);
    expect(shouldSendOnEnter({key:'Enter',shiftKey:false,keyCode:229})).toBe(false);
    expect(shouldSendOnEnter({key:'a',shiftKey:false})).toBe(false);
  });
});
