import Link from 'next/link';
import {requireUser} from '@/lib/auth';
import SessionActions from '@/components/SessionActions';
export const dynamic='force-dynamic';
export default async function Layout({children}:{children:React.ReactNode}){const user=await requireUser();return <main className="workspace"><header><Link className="wordmark" href="/funds">BlackSwan</Link><nav aria-label="Ana gezinme"><Link href="/funds">Fonlar</Link>{user.role!=='viewer'&&<Link href="/review">İnceleme kuyruğu</Link>}</nav><SessionActions/></header>{children}<footer>{user.data_mode} · Geliştirme sonucu · Veri hakları incelenmedi · Yatırım tavsiyesi değildir</footer></main>;}
