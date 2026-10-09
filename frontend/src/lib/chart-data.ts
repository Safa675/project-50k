import type {Fund} from './research-contract';
export type ChartDatum={time:string,value:number};
/** Split the line at each explicit missing point so the chart cannot bridge it. */
export function chartSegments(points:Fund['chart']['points'],key:'fund'|'peers'):ChartDatum[][]{
 const segments:ChartDatum[][]=[];let segment:ChartDatum[]=[];
 for(const point of points){const value=point[key]===null?null:Number(point[key]);if(value===null||!Number.isFinite(value)){if(segment.length)segments.push(segment);segment=[];}else segment.push({time:point.date,value});}
 if(segment.length)segments.push(segment);return segments;
}
