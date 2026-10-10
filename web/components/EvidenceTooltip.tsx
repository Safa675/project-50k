'use client';
import {useEffect,useId,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
export default function EvidenceTooltip({children,title='Kaynak ve yöntem',text,direction='bottom'}:{children:React.ReactNode;title?:string;text:string;direction?:'bottom'|'right'}){
  const id=useId(),host=useRef<HTMLSpanElement|null>(null),tip=useRef<HTMLDivElement|null>(null),timer=useRef<ReturnType<typeof setTimeout>|null>(null);const [position,setPosition]=useState<{top:number;left:number;side:'bottom'|'right'}|null>(null);
  useEffect(()=>()=>{if(timer.current)clearTimeout(timer.current);},[]);
  function keep(){if(timer.current)clearTimeout(timer.current);}
  function leave(){keep();timer.current=setTimeout(()=>setPosition(null),180);}
  function show(){const rect=host.current?.getBoundingClientRect();if(!rect)return;const side=direction==='right'&&rect.right+340<window.innerWidth?'right':'bottom';setPosition({side,left:Math.max(16,Math.min(side==='right'?rect.right+8:rect.left,window.innerWidth-336)),top:Math.max(8,Math.min(side==='right'?rect.top-28:rect.bottom+10,window.innerHeight-160))});}
  return <span ref={host} className="ev-tip-host" onMouseEnter={()=>{keep();show();}} onMouseLeave={leave} onBlur={event=>{if(!event.currentTarget.contains(event.relatedTarget)&&!tip.current?.contains(event.relatedTarget))setPosition(null);}}><button type="button" aria-describedby={position?id:undefined} aria-expanded={!!position} onFocus={show} onClick={show} onKeyDown={event=>{if(event.key==='Escape')setPosition(null);}}>{children}</button>{position&&createPortal(<div ref={tip} className={`ev-tooltip ev-tooltip-${position.side}`} role="tooltip" id={id} style={{top:position.top,left:position.left}} onMouseEnter={keep} onMouseLeave={leave} onKeyDown={event=>{if(event.key==='Escape'){setPosition(null);host.current?.querySelector('button')?.focus();}}}><img src={`/design/evidence/arrow-${position.side==='right'?'left':'top'}.svg`} alt=""/><strong>{title}</strong><p>{text}</p><a href="/method">Yöntemde oku →</a></div>,document.body)}</span>;
}
