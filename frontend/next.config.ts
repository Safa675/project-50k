import type { NextConfig } from 'next';
const apiTarget = process.env.P50K_API_ORIGIN ?? process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8767';
const target = new URL(apiTarget);
if (!['127.0.0.1','localhost','[::1]'].includes(target.hostname) || target.protocol !== 'http:') throw new Error('The research API must use a local loopback HTTP origin.');
const config: NextConfig = {
  devIndicators: false,
  agentRules: false,
  poweredByHeader: false,
  async headers() {
    return [{source:'/:path*',headers:[{key:'Cache-Control',value:'no-store'},{key:'Referrer-Policy',value:'no-referrer'},{key:'X-Content-Type-Options',value:'nosniff'}]}];
  },
  async rewrites() { return [{source:'/api/research/:path*',destination:`${target.origin}/research/:path*`}]; }
};
export default config;
