'use client';

const VENDOR_STYLES = {
  mercadolivre: {
    label: 'via Mercado Livre',
    className:
      'border-yellow-300/80 bg-yellow-50 text-yellow-900',
  },
  amazon: {
    label: 'via Amazon',
    className: 'border-slate-300 bg-slate-100 text-slate-800',
  },
};

export function VendorBadge({ vendor }) {
  const key = (vendor || '').toLowerCase();
  const config = VENDOR_STYLES[key] || {
    label: vendor ? `via ${vendor}` : 'Parceiro',
    className: 'border-slate-200 bg-slate-50 text-slate-600',
  };

  return (
    <span
      className={`inline-flex max-w-full items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${config.className}`}
    >
      {config.label}
    </span>
  );
}
