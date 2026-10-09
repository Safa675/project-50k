/** Exact comparison only; financial arithmetic remains in the validated Python bundle. */
function parts(value: string) {
  const match = /^([+-]?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match) return null;
  const fraction = match[3] ?? '';
  const digits = (match[2] + fraction).replace(/^0+/, '') || '0';
  const exponent = BigInt(match[4] ?? '0') - BigInt(fraction.length);
  const sign = digits === '0' ? 0 : match[1] === '-' ? -1 : 1;
  return {digits, exponent, sign};
}
export function compareDecimal(left: string, right: string): number {
  const a = parts(left), b = parts(right);
  if (!a || !b) return Number.NaN;
  if (a.sign !== b.sign) return a.sign > b.sign ? 1 : -1;
  if (a.sign === 0) return 0;
  const aPosition = BigInt(a.digits.length) + a.exponent;
  const bPosition = BigInt(b.digits.length) + b.exponent;
  if (aPosition !== bPosition) return (aPosition > bPosition ? 1 : -1) * a.sign;
  const length = Math.max(a.digits.length, b.digits.length);
  const aDigits = a.digits.padEnd(length, '0'), bDigits = b.digits.padEnd(length, '0');
  return (aDigits === bDigits ? 0 : aDigits > bDigits ? 1 : -1) * a.sign;
}
export function absoluteDecimal(value: string): string { return value.replace(/^[+-]/, ''); }
