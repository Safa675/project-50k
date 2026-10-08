'use client';

import {useEffect, useId, useRef, useState} from 'react';
import {ColorType, createChart, LineSeries, LineStyle, type LineData, type Time} from 'lightweight-charts';
import {chartSegments, type ChartDatum} from '@/lib/chart-data';
import {ChartSchema, type Fund} from '@/lib/research-contract';
import {date, reason} from '@/lib/presentation';
import EmptyState from '@/components/primitives/EmptyState';

type PreparedChart = {
  points: Fund['chart']['points'];
  fundSegments: ChartDatum[][];
  peerSegments: ChartDatum[][];
};

/** Rendering validates authored points; it never calculates a return or a D1 metric. */
export function prepareChart(chart: Fund['chart']): PreparedChart | null {
  const parsed = ChartSchema.safeParse(chart);
  if (!parsed.success || parsed.data.status !== 'AVAILABLE') return null;
  const first = parsed.data.points[0];
  if (!first || first.fund === null || first.peers === null ||
      Number(first.fund) !== 100 || Number(first.peers) !== 100) return null;
  if (parsed.data.points.some(point => [point.fund, point.peers].some(
    value => value !== null && !Number.isFinite(Number(value))))) return null;
  const fundSegments = chartSegments(parsed.data.points, 'fund');
  const peerSegments = chartSegments(parsed.data.points, 'peers');
  if (!fundSegments.length || !peerSegments.length) return null;
  return {points: parsed.data.points, fundSegments, peerSegments};
}

export default function FundChart({chart, synthetic = false}: {
  chart: Fund['chart']; synthetic?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null);
  const captionId = useId();
  const [renderError, setRenderError] = useState(false);
  const prepared = prepareChart(chart);

  useEffect(() => {
    const target = container.current;
    const data = prepareChart(chart);
    if (!target || !data) return;
    setRenderError(false);
    let api: ReturnType<typeof createChart> | undefined;
    try {
      api = createChart(target, {
        autoSize: true,
        layout: {background: {type: ColorType.Solid, color: '#ffffff'}, textColor: '#465b62',
          fontFamily: 'system-ui, sans-serif', attributionLogo: true},
        grid: {vertLines: {visible: false}, horzLines: {color: '#edf1ee'}},
        localization: {locale: 'tr-TR'},
        rightPriceScale: {borderColor: '#e2e9e4', scaleMargins: {top: 0.12, bottom: 0.12}},
        timeScale: {borderColor: '#e2e9e4', timeVisible: false, secondsVisible: false,
          ignoreWhitespaceIndices: false},
        handleScroll: false,
        handleScale: {axisDoubleClickReset: false, axisPressedMouseMove: false,
          mouseWheel: false, pinch: false},
      });
      // This series preserves shared-calendar positions even when both plotted
      // values are missing. It draws no line and cannot bridge either gap.
      const calendar = api.addSeries(LineSeries, {
        color: 'transparent', lastValueVisible: false, priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      calendar.setData(data.points.map(point => ({time: point.date as Time})));
      for (const [segments, color, lineStyle] of [
        [data.fundSegments, '#1b6559', LineStyle.Solid],
        [data.peerSegments, '#718b9d', LineStyle.Dashed],
      ] as const) {
        // Separate series are deliberate. A whitespace datum in one series can
        // still connect valid observations across the missing interval.
        for (const segment of segments) {
          const series = api.addSeries(LineSeries, {
            color, lineStyle, lineWidth: 2, pointMarkersVisible: segment.length === 1,
            pointMarkersRadius: 3, lastValueVisible: false, priceLineVisible: false,
            crosshairMarkerVisible: true,
            priceFormat: {type: 'price', precision: 2, minMove: 0.01},
          });
          series.setData(segment.map(point => ({time: point.time as Time, value: point.value})) as LineData<Time>[]);
        }
      }
      api.timeScale().fitContent();
    } catch {
      api?.remove();
      api = undefined;
      setRenderError(true);
    }
    return () => {api?.remove();};
  }, [chart]);

  if (!prepared) return <EmptyState title="Grafik için yeterli veri yok"
    description={chart.status === 'UNAVAILABLE' ? chart.reason ? reason(chart.reason) : 'Ortak başlangıç tarihi bulunamadı.' :
      'Grafik verileri doğrulanamadı veya sayılar çizim aralığının dışında.'}/>;

  return <figure aria-label="Fon ve kategori benzerlerinin normalleştirilmiş getirisi"
    aria-describedby={captionId} className="m-0">
    <div className="chart-legend" aria-label="Grafik göstergeleri">
      <span>Fon · düz çizgi</span><span>Kategori benzerleri · kesikli çizgi</span>
    </div>
    <div className="chart-preview" style={{padding: 0, height: 270, position: 'relative'}}>
      <div ref={container} aria-hidden="true" style={{width: '100%', height: '100%'}}/>
      {renderError ? <div role="alert" className="p-5" style={{position: 'absolute', inset: 0, background: '#fff'}}>
        Grafik çizilemedi. Aynı gözlemleri aşağıdaki tabloda inceleyebilirsiniz.
      </div> : null}
    </div>
    <figcaption id={captionId} className="detail-note">
      Ortak başlangıç = 100 · {date(chart.baseline_date)}. {chart.peer_count} benzer fon.
      {' '}Benzerler çizgisi, aynı başlangıca göre ölçeklenmiş fon fiyatlarının ortancasıdır.
      {' '}Eksik gözlemler çizgide boşluk bırakır. Bu grafik, D1’in ortanca günlük fazla getiri hesabı değildir.
      {synthetic ? ' Gösterilen gözlemler tasarım için hazırlanmış örnek veridir.' : ''}
    </figcaption>
    <details className="mt-3">
      <summary className="cursor-pointer text-sm">Grafik verilerini tablo olarak göster</summary>
      <div className="mt-3 overflow-x-auto" style={{maxHeight: 300}}>
        <table className="w-full text-sm">
          <caption className="text-left detail-note">Ortak başlangıç 100; eksik gözlemler boş bırakılmıştır</caption>
          <thead><tr><th scope="col" className="text-left">Tarih</th><th scope="col" className="text-right">Fon</th>
            <th scope="col" className="text-right">Kategori benzerleri</th></tr></thead>
          <tbody>{prepared.points.map(point => <tr key={point.date}>
            <th scope="row" className="text-left font-normal py-1">{date(point.date)}</th>
            <td className="text-right">{point.fund === null ? 'Veri yok' : Number(point.fund).toLocaleString('tr-TR', {maximumFractionDigits: 2})}</td>
            <td className="text-right">{point.peers === null ? 'Veri yok' : Number(point.peers).toLocaleString('tr-TR', {maximumFractionDigits: 2})}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </details>
  </figure>;
}
