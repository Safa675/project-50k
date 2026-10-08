import {describe,it,expect} from 'vitest';
import {syntheticFunds} from '../src/lib/synthetic';
import {matchesFund,screenLabel,percent} from '../src/lib/presentation';
describe('presentation',()=>{
 it('keeps unavailable findings unknown',()=>expect(screenLabel(syntheticFunds[3].d1)).toBe('Veri yetersiz'));
 it('preserves missing quantities',()=>expect(percent(null)).toBe('—'));
 it('keeps stale labels separate',()=>expect(screenLabel(syntheticFunds[2].d1)).toBe('Güncel gözlem eksik'));
 it('uses name/code and independent filters',()=>{expect(matchesFund(syntheticFunds[0],'aaa','Hisse senedi','two')).toBe(true);expect(matchesFund(syntheticFunds[0],'zzz','','all')).toBe(false);expect(matchesFund(syntheticFunds[3],'','','none')).toBe(false);});
});
it('matches ASCII fund codes independently of Turkish name casing',()=>{
 const fund={...syntheticFunds[0],code:'IAA',name:'İstanbul Örnek Fonu'};
 expect(matchesFund(fund,'iaa','','all')).toBe(true);
 expect(matchesFund(fund,'istanbul','','all')).toBe(true);
});
