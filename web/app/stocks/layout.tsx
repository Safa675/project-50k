import {requireUser} from '@/lib/auth';
import {DesignShell} from '@/components/DesignShell';
export const dynamic='force-dynamic';
export default async function Layout({children}:{children:React.ReactNode}){const user=await requireUser();return <DesignShell user={user}>{children}</DesignShell>;}
