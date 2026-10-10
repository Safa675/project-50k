'use client';
import {useState} from 'react';
import {post} from '@/lib/client';
export default function EvaluateButton({code}:{code:string}){const [message,setMessage]=useState('');return <><button onClick={async()=>{try{const response=await post(`/funds/${code}/evaluate`);setMessage(response.ok?'Değerlendirme kuyruğa alındı.':response.status===503?'Yapay zekâ bu kurulumda kapalı; model çağrısı yapılmadı.':'Değerlendirme başlatılamadı.');}catch{setMessage('Sunucuya erişilemiyor.');}}}>Yeniden değerlendir</button>{message&&<p role="status">{message}</p>}</>;}
