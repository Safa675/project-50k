'use client';

import {useState} from 'react';
import {resolveAssetLogo,type AssetKind} from '@/lib/asset-logos';

/** Official issuer branding. Funds use their named manager's logo. */
export default function AssetLogo({kind,code,name,size=40,className='',decorative=false}:{
  kind:AssetKind;code:string;name?:string;size?:number;className?:string;decorative?:boolean;
}){
  const logo=resolveAssetLogo(kind,code,name);
  const [failed,setFailed]=useState<string|null>(null);
  const visible=logo&&failed!==logo.path;
  const label=visible?`${kind==='fund'?'Fon yöneticisi logosu':'Şirket logosu'}: ${logo.issuer}`:code;
  return <span className={`asset-logo ${className}`} title={label}
    role={decorative?undefined:'img'} aria-label={decorative?undefined:label} aria-hidden={decorative||undefined}
    style={{display:'inline-flex',alignItems:'center',justifyContent:'center',width:size,height:size,minWidth:size,
      flexShrink:0,borderRadius:'50%',overflow:'hidden',background:visible?(logo.background??'#fff'):'var(--bs-surface-2,#2e2e32)',
      color:'var(--bs-text,#f2f2f3)',fontSize:Math.min(12,size/3.5),fontWeight:500,lineHeight:1.1,textAlign:'center'}}>
    {visible?<img src={logo.path} alt="" width={size} height={size} loading="lazy" decoding="async"
      onError={()=>setFailed(logo.path)} style={{display:'block',width:'100%',height:'100%',maxWidth:'100%',objectFit:'contain',padding:size>=48?6:4}}/>:code}
  </span>;
}
