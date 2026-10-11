import {cookies} from 'next/headers';
import {redirect} from 'next/navigation';
import {apiOrigin} from './proxy';

export type AnalysisContext={as_of_date:string;cutoff:string;mode:'historical'|'live';scope_key:string;today:string;timezone:string};
export type User = {user_id: string; email: string; role: 'viewer'|'analyst'|'admin'; avatar_path?: string|null; data_mode:string;analysis_context?:AnalysisContext};
export async function serverApi(path: string): Promise<Response> {
  const jar = await cookies();
  return fetch(`${apiOrigin()}${path}`, {headers: {Cookie: jar.toString()}, cache: 'no-store', signal: AbortSignal.timeout(10000)});
}
export async function requireUser(): Promise<User> {
  const response = await serverApi('/auth/me');
  if (response.status === 401) redirect('/login');
  if (!response.ok) throw new Error('Oturum şu anda doğrulanamıyor.');
  const data = await response.json();
  if (!data.user || !['viewer','analyst','admin'].includes(data.user.role)) throw new Error('Oturum yanıtı doğrulanamadı.');
  return {...data.user,data_mode:data.data_mode,analysis_context:data.analysis_context} as User;
}
