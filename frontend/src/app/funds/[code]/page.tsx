import {redirect} from 'next/navigation';
export default async function Page({params}:{params:Promise<{code:string}>}){redirect(`/preview?detail=${(await params).code}`);}
