'use client';

import {useEffect, useId, useRef, useState} from 'react';
import {SourceSchema, type Source} from '@/lib/research-contract';
import {sourceTitle} from '@/lib/presentation';
import PdfViewer from './PdfViewer';

const HASH = /^[a-f0-9]{64}$/;
const CUTOFF = '2026-09-16T23:59:59+03:00';

export function opaquePdfPath(source: Source, bundleId: string, cutoffAt = CUTOFF): string {
  if (!HASH.test(bundleId) || cutoffAt !== CUTOFF || !SourceSchema.safeParse(source).success ||
      !source.pdf_available || source.kind !== 'KAP_PDF' || source.media_type !== 'application/pdf') {
    throw new Error('Bu kaynağın doğrulanabilir PDF dosyası bulunmuyor.');
  }
  if (source.published_at === null || Date.parse(source.published_at) > Date.parse(cutoffAt)) {
    throw new Error('PDF’nin bu inceleme zamanından önce yayımlandığı doğrulanamadı.');
  }
  return `/api/research/v1/sources/${source.source_id}`;
}

/** Bind the exact response bytes to the already displayed source and bundle. */
export async function verifyPdfResponse(response: Response, source: Source, bundleId: string,
  cutoffAt = CUTOFF): Promise<ArrayBuffer> {
  opaquePdfPath(source, bundleId, cutoffAt);
  if (!response.ok) {
    throw new Error(response.status === 404 ? 'Orijinal PDF dosyası bulunamadı.' :
      response.status === 503 ? 'Kaynak dosyası şu anda doğrulanamıyor. Yeniden deneyebilirsiniz.' :
        'PDF yüklenemedi. Yeniden deneyebilirsiniz.');
  }
  const expectedHeaders: Record<string, string> = {
    'x-research-bundle-id': bundleId, 'x-research-cutoff-at': cutoffAt,
    'x-research-origin': 'HISTORICAL_REPLAY', 'x-research-analysis-mode': 'EXPLORATORY_ARCHIVE',
    'x-research-point-in-time-verified': 'false', 'x-research-rights-status': 'UNKNOWN',
  };
  if (Object.entries(expectedHeaders).some(([key, value]) => response.headers.get(key) !== value) ||
      !/^application\/pdf(?:;|$)/i.test(response.headers.get('content-type') ?? '') ||
      !(response.headers.get('cache-control') ?? '').toLowerCase().includes('no-store')) {
    throw new Error('PDF yanıtı görüntülenen araştırma paketiyle eşleşmiyor.');
  }
  const bytes = await response.arrayBuffer();
  const signature = new TextDecoder('ascii').decode(bytes.slice(0, 5));
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
    byte => byte.toString(16).padStart(2, '0')).join('');
  if (signature !== '%PDF-' || hash !== source.sha256) {
    throw new Error('PDF dosyası kayıtlı kaynak özetiyle eşleşmiyor.');
  }
  return bytes;
}

export default function SourcePdfDialog({source, bundleId, cutoffAt = CUTOFF, onClose}: {
  source: Source | null; bundleId: string; cutoffAt?: string; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const closeCallback = useRef(onClose);
  const [verified, setVerified] = useState<{identity: string; bytes: ArrayBuffer; url: string} | null>(null);
  const [failure, setFailure] = useState<{identity: string; message: string} | null>(null);
  const [attempt, setAttempt] = useState(0);
  const identity = `${bundleId}:${cutoffAt}:${source?.source_id}:${source?.sha256}:${attempt}`;
  const ready = verified?.identity === identity ? verified : null;
  const error = failure?.identity === identity ? failure.message : null;
  const titleId = useId();
  closeCallback.current = onClose;

  useEffect(() => {
    if (!source || !dialog.current) return;
    const modal = dialog.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!modal.open) modal.showModal();
    closeButton.current?.focus();
    return () => {
      if (modal.open) modal.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [source?.source_id]);

  useEffect(() => {
    if (!source) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    let active = true;
    setVerified(null);
    setFailure(null);
    async function load() {
      try {
        const path = opaquePdfPath(source!, bundleId, cutoffAt);
        const response = await fetch(path, {cache: 'no-store', credentials: 'omit',
          redirect: 'error', signal: controller.signal, headers: {Accept: 'application/pdf'}});
        const bytes = await verifyPdfResponse(response, source!, bundleId, cutoffAt);
        if (!active) return;
        objectUrl = URL.createObjectURL(new Blob([bytes], {type: 'application/pdf'}));
        setVerified({identity, bytes, url: objectUrl});
      } catch (problem) {
        if (!active || controller.signal.aborted) return;
        setFailure({identity, message: problem instanceof Error ? problem.message : 'PDF yüklenemedi. Yeniden deneyebilirsiniz.'});
      }
    }
    void load();
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      // Reopening the same source still requires a new no-store verification.
      setVerified(null);
      setFailure(null);
    };
  }, [source, bundleId, cutoffAt, identity]);

  if (!source) return null;
  return <dialog ref={dialog} aria-labelledby={titleId} aria-label="Orijinal kaynak PDF"
    onCancel={event => {event.preventDefault(); closeCallback.current();}}
    className="m-auto rounded-lg border border-[var(--border-subtle)] p-0 shadow-xl backdrop:bg-black/40"
    style={{width: 'min(1100px, calc(100vw - 32px))', height: 'min(90vh, 900px)', maxWidth: 'none'}}>
    <div className="flex h-full flex-col bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border-subtle)] p-4">
        <div><h2 id={titleId} className="m-0 text-base">Orijinal kaynak PDF</h2>
          <p className="detail-note m-0">{sourceTitle(source)}</p></div>
        <button ref={closeButton} type="button" className="button" onClick={() => closeCallback.current()}>Kapat</button>
      </div>
      <div className="min-h-0 flex-1">
        {error ? <div className="p-5"><p role="alert">{error}</p><button type="button" className="button"
          onClick={() => setAttempt(value => value + 1)}>Yeniden dene</button></div> : ready ?
          <PdfViewer key={identity} bytes={ready.bytes}/> :
          <p role="status" className="p-5">PDF doğrulanıyor…</p>}
      </div>
      <div className="border-t border-[var(--border-subtle)] p-4">
        {ready ? <div className="flex flex-wrap gap-2"><a href={ready.url} className="button" target="_blank" rel="noopener noreferrer">
          PDF’yi ayrı sekmede aç
        </a><a href={ready.url} className="button" download="source.pdf">Orijinal PDF’yi indir</a></div> : null}
        <p className="detail-note mb-0">Dosyanın kaynak özeti ve araştırma paketi eşleştiğinde görüntülenir.
          {' '}Bu arşiv sürümünün geçmiş erişim zamanı doğrulanmış değildir.</p>
      </div>
    </div>
  </dialog>;
}
