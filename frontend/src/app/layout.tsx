import type {Metadata} from 'next';
import IntlProvider from '@/components/IntlProvider';
import './globals.css';
export const metadata: Metadata = {title:'Fon araştırması · Project 50K', robots:{index:false,follow:false}};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="tr"><body><IntlProvider>{children}</IntlProvider></body></html>;
}
