import {afterEach,describe,it,expect,vi} from 'vitest';
import {z} from 'zod';
import {fetchValidated,loadList,ResearchApiError} from '../src/lib/research-api';
afterEach(()=>vi.unstubAllGlobals());
describe('validated JSON transport',()=>{
 it('marks runtime requests no-store',async()=>{const mock=vi.fn().mockResolvedValue(new Response('{"value":"ok"}',{status:200}));vi.stubGlobal('fetch',mock);expect(await fetchValidated('/test',z.object({value:z.string()}))).toEqual({value:'ok'});expect(mock.mock.calls[0][1]).toMatchObject({cache:'no-store',credentials:'omit'});});
 it('rejects malformed runtime payloads',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{"value":1}')));await expect(fetchValidated('/test',z.object({value:z.string()}))).rejects.toMatchObject({code:'INVALID_DATA'});});
 it('reports API network errors',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('offline')));await expect(fetchValidated('/test',z.string())).rejects.toBeInstanceOf(ResearchApiError);});
 it('preserves abort semantics',async()=>{vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new DOMException('Cancelled','AbortError')));await expect(fetchValidated('/test',z.string())).rejects.toMatchObject({name:'AbortError'});});
});
