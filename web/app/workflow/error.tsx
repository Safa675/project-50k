'use client';

export default function Error({reset}: {reset: () => void}) {
  return <section><h1>İş akışı bilgisi yüklenemedi</h1><p>Veri bağlantısı şu anda yanıt vermiyor.</p><button onClick={reset}>Tekrar dene</button></section>;
}
