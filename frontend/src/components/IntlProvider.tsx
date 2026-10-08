'use client';
import {NextIntlClientProvider} from 'next-intl';
import messages from '@/messages/tr.json';
export default function IntlProvider({children}:{children:React.ReactNode}){
 return <NextIntlClientProvider locale="tr" messages={messages} timeZone="Europe/Istanbul">{children}</NextIntlClientProvider>;
}
