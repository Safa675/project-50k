import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,expect,it} from 'vitest';
import ResultsReport,{type Report} from '../app/results/ResultsReport';
import {assessedCoverage,caseFundBreakdown,caseFundCodes} from '../app/results/results-logic';
import LegacyResults from '../app/sonuclar/page';

const counts={caught:3,missed:5,listed_not_assessable:2,flagged_outside:4,quiet:7,other_not_assessable:1,listed_funds:10,other_funds:12,flagged:7,scanned:22};
const summary={counts,detection_rate:{numerator:3,denominator:10,percent:'30.0'},on_list_share:{numerator:3,denominator:7,percent:'42.9'},other_flag_rate:{numerator:4,denominator:12,percent:'33.3'},times_more_often:'0.9'};
const report:Report={run:{scan_day:'2030-01-02',as_of:'2030-01-01',cutoff:'2030-01-02T20:59:59Z'},ground_truth:{listed_total:10,outside_scan:[],decision_date:'2030-01-07',source_urls:['https://spk.gov.tr/synthetic'],publication_dates:['2030-01-07'],publication_time_known:false,decision_references:['synthetic-reference']},summaries:{price:summary,all:summary,data_quality:summary},funds:[{fund_code:'SYN',name:'Synthetic fund',listed:true,detectors:['D1'],outcomes:{price:'caught',all:'caught',data_quality:'listed_not_assessable'},href:'/funds/SYN'}],detectors:{D1:{label:'Benzer fonlardan ayrışma',family:'price'}}};
describe('plain-language retrospective results',()=>{
  it('does not show zero-event metrics when the official list has not been imported',()=>{
    const html=renderToStaticMarkup(createElement(ResultsReport,{report:{...report,ground_truth:{...report.ground_truth,listed_total:0}}}));
    expect(html).toContain('Karşılaştırma verisi eksik');
    expect(html).toContain('doğrulanmış kayıtları bulunmuyor');
    expect(html).not.toContain('fon tarandı');
    expect(html).not.toContain('Önceden işaretlenen');
  });
  it('renders server-computed counts and separates non-flags from missing assessments',()=>{
    const html=renderToStaticMarkup(createElement(ResultsReport,{report}));
    expect(html).toContain('<strong>22</strong> fon tarandı');
    expect(html).toContain('İşaretlenmeyen</span><strong>7</strong>');
    expect(html).toContain('5 fonda sınır aşılmadı; 2 fon yeterli veri olmadığı için değerlendirilemedi.');
    expect(html).toContain('Değerlendirilemeyen</span><strong>3</strong>');
    expect(html).toContain('href="/funds/SYN"');
    expect(html).not.toContain('>D1<');
    expect(html).toContain('0,9 katıydı');
    expect(html).not.toContain('daha sık işaretlendi');
  });
  it('keeps hindsight, development limits, event learning and neutral interpretation visible',()=>{
    const html=renderToStaticMarkup(createElement(ResultsReport,{report}));
    for(const text of ['Bu karşılaştırma olaydan sonra yapılıyor.','ajan incelemelerine verilmez','usulsüzlük tespiti değildir','THF ve TP2 incelendikten sonra','Ayrı bir doğrulama grubu kullanılmadı','SPK bültenini aç'])expect(html).toContain(text);
    expect(html).not.toContain('run_id');
    expect(html).not.toContain('packet_sha256');
  });
  it('shows assessed coverage from price counts without treating missing results as assessed',()=>{
    expect(assessedCoverage({scanned:20,listed_not_assessable:2,other_not_assessable:3})).toEqual({scanned:20,assessed:15,notAssessable:5,percent:'75.0'});
    expect(assessedCoverage({scanned:0,listed_not_assessable:0,other_not_assessable:0}).percent).toBeNull();
    expect(assessedCoverage({scanned:2,listed_not_assessable:3,other_not_assessable:0}).assessed).toBeNull();
    const html=renderToStaticMarkup(createElement(ResultsReport,{report}));
    expect(html).toContain('Fiyat değerlendirmesi kapsamı');
    expect(html).toContain('%86,4');
    expect(html).toContain('19 / 22 fon');
    expect(html).toContain('3</strong> fon yeterli fiyat verisi olmadığı için değerlendirilemedi.');
  });
  it('counts case price flags separately from D1 and keeps missed, unassessable and absent records distinct',()=>{
    const funds=caseFundCodes.map((code,index)=>({fund_code:code,name:'Synthetic case fund',href:`/funds/${code}`,
      detectors:index<3?['D1']:index===3?['D2']:[],outcomes:{price:index<4?'caught':index<6?'missed':'listed_not_assessable'}}));
    const cases=caseFundBreakdown(funds);
    expect({d1:cases.d1Flagged,price:cases.caught,missed:cases.missed,unassessable:cases.notAssessable,missing:cases.missing}).toEqual({d1:3,price:4,missed:2,unassessable:2,missing:0});
    const partial=caseFundBreakdown(funds.slice(0,1));
    expect(partial.caught).toBe(1);expect(partial.missed).toBe(0);expect(partial.notAssessable).toBe(0);expect(partial.missing).toBe(7);
    expect(partial.rows[1].d1Flagged).toBeNull();
  });
  it('renders case limitations and a separate experiment slot without changing baseline counts',()=>{
    const caseFund={fund_code:'THF',name:'Synthetic case fund',listed:true,detectors:['D1'],outcomes:{price:'caught',all:'caught',data_quality:'listed_not_assessable'},href:'/funds/THF'} as Report['funds'][number];
    const html=renderToStaticMarkup(createElement(ResultsReport,{report:{...report,funds:[...report.funds,caseFund]},experimentPanel:createElement('section',null,'Synthetic separate experiment')}));
    expect(html).toContain('Sekiz vaka fonunda fiyat kontrolleri');
    expect(html).toContain('7 fonun tarama kaydı bu raporda bulunamadı');
    expect(html).toContain('İşaret kaydı bulunmaması, o kontrolün yeterli veriyle tamamlandığı anlamına gelmez.');
    expect(html).toContain('Synthetic separate experiment');
    expect(html).toContain('Önceden işaretlenen</span><strong>3');
  });
  it('permanently redirects old result links to the canonical path and preserves query values',async()=>{
    await expect(LegacyResults({searchParams:Promise.resolve({})})).rejects.toMatchObject({digest:expect.stringContaining('/results;308;')});
    await expect(LegacyResults({searchParams:Promise.resolve({view:'price',fund:['THF','TP2']})})).rejects.toMatchObject({digest:expect.stringContaining('/results?view=price&fund=THF&fund=TP2;308;')});
  });
});
