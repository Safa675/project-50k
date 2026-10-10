import type {Metadata} from 'next';
import './globals.css';
import './product.css';
import './design.css';

export const metadata: Metadata = {
  title: 'BlackSwan',
  description: 'Türkiye yatırım fonları ve BIST 30 hisseleri için kaynaklarıyla birlikte kanıt verisi ve kurumsal API erişimi.',
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return <html lang="tr" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:"try{document.documentElement.dataset.theme=localStorage.getItem('blackswan-theme')==='light'?'light':'dark'}catch{}"}}/></head><body>{children}</body></html>;
}
