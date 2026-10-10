import FundDecision from '@/components/FundDecision';
export default async function Layout({children,params}:{children:React.ReactNode;params:Promise<{code:string}>}){const {code}=await params;return <>{children}{/^[A-Z0-9]{2,12}$/.test(code)&&<section><FundDecision code={code}/></section>}</>;}
