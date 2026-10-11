import {permanentRedirect} from 'next/navigation';

/** Preserve saved links to the previous Turkish route. */
export default async function LegacyResults({searchParams}:{searchParams:Promise<Record<string,string|string[]|undefined>>}){
  const query=new URLSearchParams();
  for(const [key,value] of Object.entries(await searchParams))for(const item of Array.isArray(value)?value:value===undefined?[]:[value])query.append(key,item);
  permanentRedirect(`/results${query.size?`?${query}`:''}`);
}
