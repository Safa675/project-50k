import {describe,expect,it} from 'vitest';
import {compareDecimal,absoluteDecimal} from '../src/lib/decimal-compare';
describe('exact boundary comparison',()=>{
 it('distinguishes boundaries below JS float precision',()=>{expect(compareDecimal('0.10000000000000000000001','0.10')).toBe(1);expect(compareDecimal('0.09999999999999999999999','0.10')).toBe(-1);expect(compareDecimal('1e-1','0.10')).toBe(0);});
 it('handles signs, scientific strings and zero',()=>{expect(compareDecimal('-1','0.1')).toBe(-1);expect(compareDecimal('-0','+0')).toBe(0);expect(compareDecimal('-2','-1')).toBe(-1);expect(absoluteDecimal('-1.01e-2')).toBe('1.01e-2');});
 it('does not allocate huge exponent padding',()=>expect(compareDecimal('1e-999999999','1e-999999998')).toBe(-1));
});
