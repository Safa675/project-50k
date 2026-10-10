import Link from 'next/link';

export default function NotFound() {
  return <section><h1>Hisse kaydı bulunamadı</h1>
    <p>Hisse kodunu kontrol ederek güncel BIST 30 kataloğundan bir kayıt açabilirsiniz.</p>
    <Link href="/stocks">Hisse kataloğuna dön</Link>
  </section>;
}
