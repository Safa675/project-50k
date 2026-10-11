import {serverApi,type User} from './auth';

export async function optionalUser():Promise<User|undefined>{
  try{const response=await serverApi('/auth/me');if(!response.ok)return undefined;const data=await response.json();if(!data.user||!['viewer','analyst','admin'].includes(data.user.role))return undefined;return {...data.user,data_mode:data.data_mode,analysis_context:data.analysis_context} as User;}catch{return undefined;}
}
