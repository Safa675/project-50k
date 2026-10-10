import {describe, expect, it} from 'vitest';
import {ChatError, readChatAnswer} from '../lib/chat-stream';

const result = {thread_id: '00000000-0000-4000-8000-000000000001', content: 'Mevcut kanıtın kapsamı sınırlıdır.', evidence_ids: ['ev:synthetic'], model: 'synthetic-test-model'};
function response(parts: string[], newline = '\n'): Response {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({start(controller) {
    for (const part of parts) controller.enqueue(encoder.encode(part.replaceAll('\n', newline)));
    controller.close();
  }}), {headers: {'content-type': 'text/event-stream; charset=utf-8'}});
}

describe('validated chat stream', () => {
  it('shows a checked paragraph before completion, then requires a matching final answer', async () => {
    let send:ReadableStreamDefaultController<Uint8Array>;
    const encoder=new TextEncoder();
    const incoming=new ReadableStream<Uint8Array>({start(controller){send=controller;}});
    const seen:string[]=[];
    const reading=readChatAnswer(new Response(incoming,{headers:{'content-type':'text/event-stream'}}),()=>undefined,item=>seen.push(item.content));
    send!.enqueue(encoder.encode(`event: paragraph\ndata: ${JSON.stringify({index:0,content:result.content,evidence_ids:result.evidence_ids})}\n\n`));
    await new Promise(resolve=>setTimeout(resolve,0));
    expect(seen).toEqual([result.content]);
    send!.enqueue(encoder.encode(`event: answer\ndata: ${JSON.stringify(result)}\n\n`));
    expect(await reading).toEqual(result);
  });

  it('resets rejected attempts and rejects changed final content or out-of-order paragraphs',async()=>{
    const paragraph={index:0,content:result.content,evidence_ids:result.evidence_ids};
    const frame=`event: paragraph\ndata: ${JSON.stringify(paragraph)}\n\n`;
    let reset=0;
    expect(await readChatAnswer(response([frame,'event: reset\ndata: {}\n\n',`event: answer\ndata: ${JSON.stringify(result)}\n\n`]),()=>undefined,()=>undefined,()=>reset++)).toEqual(result);
    expect(reset).toBe(1);
    await expect(readChatAnswer(response([frame,`event: answer\ndata: ${JSON.stringify({...result,content:'Changed text'})}\n\n`]),()=>undefined)).rejects.toMatchObject({code:'STREAM_INVALID'});
    await expect(readChatAnswer(response([`event: paragraph\ndata: ${JSON.stringify({...paragraph,index:1})}\n\n`]),()=>undefined)).rejects.toMatchObject({code:'STREAM_INVALID'});
  });
  it('assembles fragmented UTF-8 frames and exposes tools before the complete answer', async () => {
    const events = `: keep-alive\n\nevent: tool\ndata: {"name":"get_signals"}\n\nevent: answer\ndata: ${JSON.stringify(result)}\n\n`;
    const encoded = new TextEncoder().encode(events);
    const stream = new ReadableStream<Uint8Array>({start(controller) {
      // One-byte chunks split Turkish multi-byte letters and event delimiters.
      for (const byte of encoded) controller.enqueue(Uint8Array.of(byte));
      controller.close();
    }});
    const tools: string[] = [];
    expect(await readChatAnswer(new Response(stream, {headers: {'content-type': 'text/event-stream'}}), name => tools.push(name))).toEqual(result);
    expect(tools).toEqual(['get_signals']);
  });

  it('accepts CRLF and cancels after the validated answer without waiting for EOF', async () => {
    let cancelled = false;
    const stream = new ReadableStream<Uint8Array>({start(controller) {
      controller.enqueue(new TextEncoder().encode(`event: answer\r\ndata: ${JSON.stringify(result)}\r\n\r\n`));
    }, cancel() {cancelled = true;}});
    expect(await readChatAnswer(new Response(stream, {headers: {'content-type': 'text/event-stream'}}), () => undefined)).toEqual(result);
    expect(cancelled).toBe(true);
  });

  it('never exposes partial text, malformed answers or unknown tool names', async () => {
    for (const frame of [
      'event: delta\ndata: {"content":"unvalidated text"}\n\n',
      'event: tool\ndata: {"name":"run_sql"}\n\n',
      `event: answer\ndata: ${JSON.stringify({...result, thread_id: 'other-user-thread'})}\n\n`,
      'event: answer\ndata: not-json\n\n',
    ]) await expect(readChatAnswer(response([frame]), () => undefined)).rejects.toMatchObject({code: 'STREAM_INVALID'});
  });

  it('reports explicit server failures and truncated streams without manufacturing an answer', async () => {
    await expect(readChatAnswer(Response.json({error: 'AI_OFF'}, {status: 503}), () => undefined)).rejects.toMatchObject({code: 'AI_OFF'});
    await expect(readChatAnswer(Response.json({detail: 'AI_OFF'}, {status: 503}), () => undefined)).rejects.toMatchObject({code: 'AI_OFF'});
    await expect(readChatAnswer(response(['event: error\ndata: {"code":"ANSWER_INVALID"}\n\n']), () => undefined)).rejects.toMatchObject({code: 'ANSWER_INVALID'});
    await expect(readChatAnswer(response(['event: answer\ndata: {']), () => undefined)).rejects.toBeInstanceOf(ChatError);
    await expect(readChatAnswer(response(['event: answer\ndata: {']), () => undefined)).rejects.toMatchObject({code: 'STREAM_INTERRUPTED'});
  });

  it('bounds frames and tool activity before rendering content', async () => {
    await expect(readChatAnswer(response(['x'.repeat(32769)]), () => undefined)).rejects.toMatchObject({code: 'STREAM_INVALID'});
    await expect(readChatAnswer(response(['event: tool\ndata: {"name":"search_funds"}\n\n'.repeat(7)]), () => undefined)).rejects.toMatchObject({code: 'STREAM_INVALID'});
  });
});
