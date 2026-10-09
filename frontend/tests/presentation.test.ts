import {describe,it,expect} from 'vitest';
import {syntheticFunds} from '../src/lib/synthetic';
import {matchesFund,screenLabel,percent,sourceTitle,reportedPdfPeriod} from '../src/lib/presentation';
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
it('uses only a bounded declared PDF filename month, never publication time',()=>{
 expect(reportedPdfPeriod('2026-07_900000001.pdf')).toBe('2026-07');
 expect(reportedPdfPeriod('2026-13_900000001.pdf')).toBeNull();
 expect(reportedPdfPeriod('2026-071_extra.pdf')).toBeNull();
 expect(reportedPdfPeriod('authored-report.pdf')).toBeNull();
 expect(sourceTitle({kind:'KAP_PDF',fund_code:'AAA',file_name:'2026-07_900000001.pdf'})).toContain('Temmuz 2026');
});
it('distinguishes notification lists from monthly numeric series',()=>{
 expect(sourceTitle({kind:'KAP_SERIES',fund_code:'AAA',file_name:'kap_report_list.json'})).toContain('KAP bildirim listesi');
 expect(sourceTitle({kind:'KAP_SERIES',fund_code:'AAA',file_name:'kap_portfolio_reports_AAA.json'})).toContain('KAP bildirim listesi');
 expect(sourceTitle({kind:'KAP_SERIES',fund_code:'AAA',file_name:'AAA.json'})).toContain('PDF’den çıkarılan aylık veriler');
});
