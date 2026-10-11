import {ChatError} from './chat-stream';

export type StoredChatMessage = {role:'user'|'assistant';content:string;evidence_ids:string[];
  evidence_labels?:Record<string,string>;message_id?:string;created_at?:string;
  status?:'VALID'|'FAILED'|'PENDING'|'INTERRUPTED';error_code?:string|null;clientKey?:string};
export type ChatThread = {thread_id:string;created_at:string;last_message_at:string|null;message_count:number;title:string};
export const threadIdPattern=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
export function validScope(value:unknown):value is string{return typeof value==='string'&&/^(live|asof:\d{4}-\d{2}-\d{2})$/.test(value);}
function record(value:unknown):value is Record<string,unknown>{return value!==null&&typeof value==='object'&&!Array.isArray(value);}
// A null code is the Raportör's general conversation: the server must answer with no fund.
function sameAsset(value:unknown,code:string|null):boolean{return code===null?value===null||value===undefined:value===code;}
function scoped(value:unknown,code:string|null,scope?:string):asserts value is Record<string,unknown>{
  if(!record(value)||!sameAsset(value.fund_code,code)||!validScope(value.analysis_scope_key)||(scope!==undefined&&value.analysis_scope_key!==scope))throw new ChatError('HISTORY_SCOPE_CHANGED');
}
function timestamp(value:unknown):value is string{return typeof value==='string'&&value.length<=50&&Number.isFinite(Date.parse(value));}
export function parseChatThreads(value:unknown,code:string|null,scope?:string):{items:ChatThread[];analysis_scope_key:string}{
  scoped(value,code,scope);
  if(!Array.isArray(value.items)||value.items.length>20||value.items.some(item=>!record(item)||
    typeof item.thread_id!=='string'||!threadIdPattern.test(item.thread_id)||!timestamp(item.created_at)||
    (item.last_message_at!==null&&!timestamp(item.last_message_at))||typeof item.title!=='string'||item.title.length>120||
    typeof item.message_count!=='number'||!Number.isSafeInteger(item.message_count)||item.message_count<0))throw new ChatError('HISTORY_INVALID');
  return {items:value.items as ChatThread[],analysis_scope_key:value.analysis_scope_key as string};
}
export function parseChatHistory(value:unknown,code:string|null,thread:string,scope:string):StoredChatMessage[]{
  scoped(value,code,scope);
  if(value.thread_id!==thread||!Array.isArray(value.items)||value.items.length>60)throw new ChatError('HISTORY_INVALID');
  for(const item of value.items){
    if(!record(item)||!['user','assistant'].includes(String(item.role))||typeof item.content!=='string'||!item.content.trim()||item.content.length>24000||
      typeof item.message_id!=='string'||!/^\d+$/.test(item.message_id)||!timestamp(item.created_at)||
      !['VALID','FAILED','PENDING','INTERRUPTED'].includes(String(item.status))||(item.role==='assistant'&&item.status!=='VALID')||
      !Array.isArray(item.evidence_ids)||item.evidence_ids.length>32||!item.evidence_ids.every(id=>typeof id==='string'&&id.length>0&&id.length<=160))throw new ChatError('HISTORY_INVALID');
    if(item.evidence_labels!==undefined&&(!record(item.evidence_labels)||Object.entries(item.evidence_labels).some(([id,label])=>!(item.evidence_ids as string[]).includes(id)||typeof label!=='string'||label.length>200)))throw new ChatError('HISTORY_INVALID');
  }
  return value.items as StoredChatMessage[];
}
export function shouldSendOnEnter(event:{key:string;shiftKey:boolean;isComposing?:boolean;keyCode?:number}):boolean{
  return event.key==='Enter'&&!event.shiftKey&&!event.isComposing&&event.keyCode!==229;
}
/** Query string for the persisted Raportör conversation of one fund, or the general one. */
export function chatAssetQuery(code:string|null):string{return code?`fund_code=${encodeURIComponent(code)}`:'';}
