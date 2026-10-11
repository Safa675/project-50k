import {describe,expect,it} from 'vitest';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {explainResult,resultStatus} from '../lib/method-explanations';
import FundReportSeries,{FundReportPoint} from '../components/FundReportSeries';

describe('user-facing analysis states',()=>{
  it('separates a computed comparison from missing inputs and price availability',()=>{
    const result={detector_id:'D1',state:'NOT_TRIGGERED',reason:'WITHIN_THRESHOLD',value:'0.001',threshold:'0.01'};
    expect(resultStatus(result)).toBe('Karşılaştırma tamamlandı');
    expect(explainResult(result)).toContain('Son 60 tarih');
    expect(resultStatus({...result,state:'ABSTAINED',reason:'CURRENT_INPUT_OR_HISTORY_UNAVAILABLE',value:null})).toBe('Bilgi yetersiz');
    expect(resultStatus({...result,value:null})).toBe('Sonuç değerlendirilemiyor');
    expect(explainResult({...result,value:null})).toContain('değişim olmadığı anlamına gelmez');
    expect(resultStatus({...result,detector_id:'AN-DQ-002',reason:'LATEST_NAV_AVAILABLE'})).toBe('Son fiyat mevcut');
  });
  it('describes the lower-bound comparison in the correct direction',()=>{
    const normal={detector_id:'D4',state:'NOT_TRIGGERED',reason:'WITHIN_THRESHOLD',value:'0.7',threshold:'0.3'};
    expect(explainResult(normal)).toContain('alt sınırın altına düşmedi');
    expect(explainResult({...normal,state:'TRIGGERED',reason:'THRESHOLD_EXCEEDED'})).toContain('alt sınırın altında kaldı');
  });
});

function report(period:string,end:string|null,value:string|null,status='AVAILABLE'):FundReportPoint{return {report_period:period,period_end:end,total_value:value,units_outstanding:null,cadence:'monthly',published_at:null,available_at:null,source_url:null,source_sha256:'synthetic-source',status,missing_fields:value===null?['total_value']:[]};}
describe('real periodic report presentation',()=>{
  it('breaks monthly lines across absent and missing reports and keeps actual zero values',()=>{
    const html=renderToStaticMarkup(createElement(FundReportSeries,{items:[report('2030-01','2030-01-31','0'),report('2030-03','2030-03-31','12'),report('2030-04','2030-04-30',null),report('2030-05','2030-05-31','16')]}));
    expect(html.match(/<polyline/g)).toHaveLength(3);
    expect(html).toContain('<td>0</td>');
    expect(html).toContain('Raporda okunamadı');
    expect(html).not.toContain('synthetic-source');
  });
  it('does not invent weekly valuation dates or an empty chart',()=>{
    const html=renderToStaticMarkup(createElement(FundReportSeries,{items:[{...report('2030-W01',null,'20'),cadence:'weekly'}]}));
    expect(html).toContain('2030-W01');
    expect(html).not.toContain('<svg');
    expect(html).toContain('tam değerleme günü doğrulanmadığı');
    expect(renderToStaticMarkup(createElement(FundReportSeries,{items:[]}))).toBe('');
  });
});
