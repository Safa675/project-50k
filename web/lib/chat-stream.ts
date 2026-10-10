export type ChatAnswer = {
  thread_id: string;
  content: string;
  evidence_ids: string[];
  model: string;
  evidence_labels?: Record<string,string>;
};

export type ChatParagraph = {index:number;content:string;evidence_ids:string[]};
export type ChatThreadStarted = {thread_id:string;analysis_scope_key:string};

export class ChatError extends Error {
  constructor(public readonly code: string) {super(code); this.name = 'ChatError';}
}

const MAX_STREAM_BYTES = 256 * 1024;
const MAX_FRAME_CHARS = 32768;
const TOOL_NAMES = new Set(['search_funds', 'get_fund_profile', 'get_signals', 'get_decision']);

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function answer(value: unknown): ChatAnswer {
  if (!object(value) || typeof value.thread_id !== 'string' ||
      !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(value.thread_id) ||
      typeof value.content !== 'string' || !value.content.trim() || value.content.length > 24000 ||
      typeof value.model !== 'string' || !value.model || value.model.length > 120 ||
      !Array.isArray(value.evidence_ids) || value.evidence_ids.length > 32 ||
      !value.evidence_ids.every(id => typeof id === 'string' && id.length > 0 && id.length <= 160) ||
      (value.evidence_labels!==undefined&&(!object(value.evidence_labels)||
        Object.entries(value.evidence_labels).some(([key,label])=>!(value.evidence_ids as unknown[]).includes(key)||typeof label!=='string'||!label.trim()||label.length>200)))) {
    throw new ChatError('STREAM_INVALID');
  }
  return value as ChatAnswer;
}

// Only complete server-validated paragraphs are displayable; raw token deltas
// remain invalid. The final persisted answer must match the streamed paragraphs.
export async function readChatAnswer(response: Response, onTool: (name: string) => void,
  onParagraph: (paragraph:ChatParagraph)=>void=()=>undefined,onReset:()=>void=()=>undefined,
  onThread:(thread:ChatThreadStarted)=>void=()=>undefined): Promise<ChatAnswer> {
  if (!response.ok) {
    let code = response.status === 401 ? 'AUTHENTICATION_REQUIRED' : 'CHAT_UNAVAILABLE';
    try {
      const data: unknown = await response.json();
      if (object(data)) {
        const error = data.error ?? data.detail;
        if (typeof error === 'string' && /^[A-Z_]{1,80}$/.test(error)) code = error;
      }
    } catch { /* A proxy may return an empty error response. */ }
    throw new ChatError(code);
  }
  if (response.headers.get('content-type')?.split(';')[0].trim() !== 'text/event-stream' || !response.body) {
    throw new ChatError('STREAM_INVALID');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8', {fatal: true});
  let buffer = '', byteCount = 0, toolCount = 0;
  let paragraphs:ChatParagraph[]=[];
  let resetCount=0;
  let startedThread:string|null=null;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) throw new ChatError('STREAM_INTERRUPTED');
      byteCount += value.length;
      if (byteCount > MAX_STREAM_BYTES) throw new ChatError('STREAM_INVALID');
      buffer += decoder.decode(value, {stream: true});
      while (true) {
        const separator = /\r?\n\r?\n/.exec(buffer);
        if (!separator) break;
        const frame = buffer.slice(0, separator.index);
        buffer = buffer.slice(separator.index + separator[0].length);
        if (frame.length > MAX_FRAME_CHARS) throw new ChatError('STREAM_INVALID');
        let event = '', data = '';
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith('event:')) event = line.slice(6).trim();
          if (line.startsWith('data:')) data += `${line.slice(5).trimStart()}\n`;
        }
        if (!data) continue; // Comment-only keep-alive frames carry no model text.
        let payload: unknown;
        try {payload = JSON.parse(data);} catch {throw new ChatError('STREAM_INVALID');}
        if(event==='thread'){
          if(startedThread!==null||!object(payload)||typeof payload.thread_id!=='string'||
            !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(payload.thread_id)||
            typeof payload.analysis_scope_key!=='string'||!/^(live|asof:\d{4}-\d{2}-\d{2})$/.test(payload.analysis_scope_key))throw new ChatError('STREAM_INVALID');
          startedThread=payload.thread_id;onThread(payload as ChatThreadStarted);
        } else if (event === 'tool') {
          if (!object(payload) || typeof payload.name !== 'string' || !TOOL_NAMES.has(payload.name) || ++toolCount > 6) {
            throw new ChatError('STREAM_INVALID');
          }
          onTool(payload.name);
        } else if (event === 'paragraph') {
          if(!object(payload)||payload.index!==paragraphs.length||paragraphs.length>=4||
            typeof payload.content!=='string'||!payload.content.trim()||payload.content.length>12000||
            !Array.isArray(payload.evidence_ids)||!payload.evidence_ids.length||payload.evidence_ids.length>8||
            !payload.evidence_ids.every(id=>typeof id==='string'&&id.length>0&&id.length<=100))throw new ChatError('STREAM_INVALID');
          const paragraph=payload as ChatParagraph;
          paragraphs.push(paragraph);onParagraph(paragraph);
        } else if(event==='reset'){
          if(!object(payload)||Object.keys(payload).length||++resetCount>3)throw new ChatError('STREAM_INVALID');
          paragraphs=[];onReset();
        } else if (event === 'answer') {
          const result=answer(payload);
          if(startedThread!==null&&result.thread_id!==startedThread)throw new ChatError('STREAM_INVALID');
          if(paragraphs.length&&(result.content!==paragraphs.map(item=>item.content).join('\n\n')||
            paragraphs.some(item=>item.evidence_ids.some(id=>!result.evidence_ids.includes(id)))))throw new ChatError('STREAM_INVALID');
          return result;
        } else if (event === 'error') {
          throw new ChatError(object(payload) && typeof payload.code === 'string' && /^[A-Z_]{1,80}$/.test(payload.code)
            ? payload.code : 'CHAT_UNAVAILABLE');
        } else {
          throw new ChatError('STREAM_INVALID');
        }
      }
      if (buffer.length > MAX_FRAME_CHARS) throw new ChatError('STREAM_INVALID');
    }
  } catch (error) {
    if (error instanceof ChatError || error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ChatError('STREAM_INTERRUPTED');
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
