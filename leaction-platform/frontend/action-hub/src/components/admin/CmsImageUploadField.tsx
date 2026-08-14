'use client';

import { useRef, useState } from 'react';
import { ImagePlus, Loader2, Upload } from 'lucide-react';
import { uploadCmsImage } from '@/lib/admin-api';

type CmsImageUploadFieldProps = {
  label: string;
  value: string;
  onChange: (url: string) => void;
  token: string | null | undefined;
  /** Prefer absolute public_url (posts) vs relative /images/... (site CMS) */
  preferPublicUrl?: boolean;
  helpText?: string;
};

export function CmsImageUploadField({
  label,
  value,
  onChange,
  token,
  preferPublicUrl = true,
  helpText,
}: CmsImageUploadFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const field =
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-emerald-400/30 transition focus:border-emerald-400 focus:ring-2';

  async function onFileSelected(file: File | null) {
    if (!file || !token) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadCmsImage(token, file);
      const next = preferPublicUrl
        ? result.public_url || result.url
        : result.url || result.public_url;
      if (!next) {
        throw new Error('Upload sem URL retornada');
      }
      onChange(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no upload');
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="space-y-2">
      <span className="text-xs font-bold uppercase tracking-wider text-stone-500">
        {label}
      </span>

      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => void onFileSelected(e.target.files?.[0] || null)}
        />
        <button
          type="button"
          disabled={uploading || !token}
          onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-800 shadow-sm transition hover:bg-stone-50 disabled:opacity-50"
        >
          {uploading ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Upload className="size-4" aria-hidden />
          )}
          {uploading ? 'Enviando…' : 'Fazer Upload'}
        </button>
        <span className="text-xs text-stone-400">PNG, JPG, WEBP · máx. 5 MB</span>
      </div>

      {helpText ? <p className="text-xs text-stone-500">{helpText}</p> : null}
      {error ? <p className="text-xs font-medium text-red-600">{error}</p> : null}

      {value ? (
        <div className="overflow-hidden rounded-xl border border-stone-200 bg-stone-50">
          <div className="flex items-center gap-3 p-3">
            <div className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white ring-1 ring-stone-200">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={value} alt="" className="size-full object-cover" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-1 text-xs font-semibold text-stone-700">
                <ImagePlus className="size-3.5 text-emerald-500" aria-hidden />
                Imagem salva
              </p>
              <p className="mt-0.5 truncate font-mono text-[11px] text-stone-500">{value}</p>
              <button
                type="button"
                className="mt-1 text-xs font-semibold text-red-600 hover:underline"
                onClick={() => onChange('')}
              >
                Remover
              </button>
            </div>
          </div>
        </div>
      ) : (
        <input
          className={field}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Ou cole uma URL (opcional)"
        />
      )}
    </div>
  );
}
