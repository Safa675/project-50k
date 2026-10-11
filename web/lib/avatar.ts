// Same-origin header photos only; the API and migration 014 enforce the identical pattern.
export const AVATAR_PATH=/^\/avatars\/[a-z0-9][a-z0-9-]{0,39}\.(jpg|png|webp)$/;
export function avatarSource(value:unknown):string|null{return typeof value==='string'&&value.trim()===value&&AVATAR_PATH.test(value)?value:null;}
export function accountInitials(email:string):string{return email.slice(0,2).toLocaleUpperCase('tr-TR');}
