'use client';

import {useEffect, useRef, useState} from 'react';
import type {PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask} from 'pdfjs-dist';

const ASSETS = '/pdfjs/6.4.299/';

/** Render only bytes already verified against the private source manifest. */
export default function PdfViewer({bytes}: {bytes: ArrayBuffer}) {
  const viewport = useRef<HTMLDivElement>(null);
  const canvasHost = useRef<HTMLDivElement>(null);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [width, setWidth] = useState(0);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState('');

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const measure = () => setWidth(Math.max(1, Math.floor(element.clientWidth - 32)));
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let active = true;
    let task: PDFDocumentLoadingTask | null = null;
    setPdf(null);
    setPage(1);
    setZoom(1);
    setLoading(true);
    setError(null);
    setText('');
    canvasHost.current?.replaceChildren();
    async function load() {
      try {
        // Import in the browser; PDF.js relies on DOM APIs absent during SSR.
        const library = await import('pdfjs-dist');
        if (!active) return;
        library.GlobalWorkerOptions.workerSrc = `${ASSETS}pdf.worker.min.mjs`;
        task = library.getDocument({
          // The worker transfers this copy, leaving verified download bytes intact.
          data: new Uint8Array(bytes.slice(0)),
          cMapUrl: `${ASSETS}cmaps/`, cMapPacked: true,
          standardFontDataUrl: `${ASSETS}standard_fonts/`,
          wasmUrl: `${ASSETS}wasm/`, iccUrl: `${ASSETS}iccs/`,
          withCredentials: false, useWorkerFetch: true, enableXfa: false,
        });
        task.onPassword = () => {
          if (active) {
            setLoading(false);
            setError('Şifreli PDF bu görüntüleyicide açılamıyor. Orijinal dosyayı indirebilirsiniz.');
          }
          void task?.destroy().catch(() => undefined);
        };
        const document = await task.promise;
        if (active) setPdf(document);
      } catch {
        if (!active) return;
        setLoading(false);
        setError(current => current ?? 'PDF görüntülenemedi. Yeniden deneyebilir veya orijinal dosyayı indirebilirsiniz.');
      }
    }
    void load();
    return () => {
      active = false;
      void task?.destroy().catch(() => undefined);
    };
  }, [bytes, attempt]);

  useEffect(() => {
    if (!pdf || !width || !canvasHost.current) return;
    let active = true;
    let rendering: RenderTask | null = null;
    const host = canvasHost.current;
    // A fresh canvas prevents simultaneous render tasks sharing a surface.
    const canvas = document.createElement('canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', `PDF sayfası ${page}`);
    canvas.style.display = 'none';
    canvas.style.maxWidth = 'none';
    host.replaceChildren(canvas);
    setLoading(true);
    setError(null);
    setText('');
    async function render() {
      try {
        const documentPage = await pdf!.getPage(page);
        if (!active) return;
        const original = documentPage.getViewport({scale: 1});
        const fitted = documentPage.getViewport({scale: width / original.width * zoom});
        if (![fitted.width, fitted.height].every(value => Number.isFinite(value) && value > 0)) {
          throw new Error('Invalid page dimensions');
        }
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2,
          Math.sqrt(16_777_216 / (fitted.width * fitted.height)));
        canvas.width = Math.max(1, Math.ceil(fitted.width * pixelRatio));
        canvas.height = Math.max(1, Math.ceil(fitted.height * pixelRatio));
        canvas.style.width = `${fitted.width}px`;
        canvas.style.height = `${fitted.height}px`;
        rendering = documentPage.render({canvas, viewport: fitted,
          transform: [pixelRatio, 0, 0, pixelRatio, 0, 0]});
        await rendering.promise;
        if (!active) return;
        canvas.style.display = 'block';
        setLoading(false);
        const content = await documentPage.getTextContent().catch(() => null);
        if (!active) return;
        setText(content?.items.map(item => 'str' in item ? item.str : '').filter(Boolean).join(' ') ?? '');
      } catch {
        if (!active) return;
        canvas.remove();
        setLoading(false);
        setError('PDF sayfası görüntülenemedi. Yeniden deneyebilir veya orijinal dosyayı indirebilirsiniz.');
      }
    }
    void render();
    return () => {
      active = false;
      rendering?.cancel();
      canvas.remove();
    };
  }, [pdf, page, width, zoom]);

  return <section className="flex h-full min-h-0 flex-col" aria-label="Doğrulanmış PDF görüntüleyici">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] px-4 py-2">
      <div className="flex items-center gap-2">
        <button type="button" className="button" disabled={!pdf || page <= 1}
          onClick={() => setPage(value => Math.max(1, value - 1))}>Önceki sayfa</button>
        <span aria-live="polite">{pdf ? `Sayfa ${page} / ${pdf.numPages}` : 'Sayfalar yükleniyor…'}</span>
        <button type="button" className="button" disabled={!pdf || page >= pdf.numPages}
          onClick={() => setPage(value => Math.min(pdf?.numPages ?? 1, value + 1))}>Sonraki sayfa</button>
      </div>
      <div className="flex items-center gap-2">
        <button type="button" className="button" disabled={!pdf || zoom <= 0.5}
          onClick={() => setZoom(value => Math.max(0.5, value - 0.25))}>Küçült</button>
        <span aria-label="Yakınlaştırma">%{Math.round(zoom * 100)}</span>
        <button type="button" className="button" disabled={!pdf || zoom >= 2}
          onClick={() => setZoom(value => Math.min(2, value + 0.25))}>Büyüt</button>
      </div>
    </div>
    <div ref={viewport} className="min-h-0 flex-1 overflow-auto bg-slate-100 p-4">
      {loading && !error ? <p role="status">PDF sayfası hazırlanıyor…</p> : null}
      {error ? <div><p role="alert">{error}</p><button type="button" className="button"
        onClick={() => setAttempt(value => value + 1)}>Yeniden dene</button></div> : null}
      <div ref={canvasHost} className="mx-auto w-fit bg-white shadow-sm"/>
      {!loading && !error ? <details className="mt-4 rounded border border-[var(--border-subtle)] bg-white p-3">
        <summary>Sayfanın metnini göster</summary>
        <p className="whitespace-pre-wrap break-words">{text || 'Bu sayfada çıkarılabilir metin bulunmuyor.'}</p>
      </details> : null}
    </div>
  </section>;
}
