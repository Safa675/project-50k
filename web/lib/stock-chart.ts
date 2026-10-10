export type StockPoint = {
  effective_date: string;
  close: string|null;
  available_at: string|null;
  source_sha256: string;
  ambiguous_revision: boolean;
};

type Coordinate = {x: number; y: number};
export function stockSeries(points: StockPoint[]): Coordinate[][] {
  const values = points.map(point => point.close === null || point.ambiguous_revision ? null : Number(point.close));
  const known = values.filter((value): value is number => value !== null && Number.isFinite(value) && value > 0);
  if (!known.length) return [];
  const low = Math.min(...known), high = Math.max(...known);
  const segments: Coordinate[][] = [];
  let segment: Coordinate[] = [];
  for (const [index, value] of values.entries()) {
    if (value === null || !Number.isFinite(value) || value <= 0) {
      if (segment.length) segments.push(segment);
      segment = [];
      continue;
    }
    segment.push({x: 30 + index * 740 / Math.max(1, points.length - 1),
      y: high === low ? 115 : 200 - (value - low) * 170 / (high - low)});
  }
  if (segment.length) segments.push(segment);
  return segments;
}
