'use client';
export default function ErrorPage({reset}: {reset: () => void}) {
  return <section role="alert"><h1>Ajan ekibi şu anda gösterilemiyor</h1>
    <p>Bağlantıyı kontrol edip yeniden deneyin. Ekibin çalışması bu sayfanın yüklenmesine bağlı değildir.</p>
    <button onClick={reset}>Yeniden dene</button>
  </section>;
}
