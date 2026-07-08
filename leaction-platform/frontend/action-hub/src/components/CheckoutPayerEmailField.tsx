'use client';

import { Mail } from 'lucide-react';

type CheckoutPayerEmailFieldProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

/** E-mail do pagador — obrigatório para o Brick do Mercado Pago liberar os campos do cartão. */
export function CheckoutPayerEmailField({
  value,
  onChange,
  disabled = false,
}: CheckoutPayerEmailFieldProps) {
  const valid = value.trim().includes('@');

  return (
    <div className="mb-6">
      <label htmlFor="checkout-payer-email" className="mb-2 block text-sm font-semibold text-slate-700">
        E-mail para cobrança e nota fiscal
      </label>
      <div className="relative">
        <Mail
          className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-slate-400"
          aria-hidden
        />
        <input
          id="checkout-payer-email"
          type="email"
          autoComplete="email"
          placeholder="voce@empresa.com"
          disabled={disabled}
          className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-red-600 focus:ring-2 focus:ring-red-600/20 disabled:cursor-not-allowed disabled:bg-slate-100"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
      {!valid ? (
        <p className="mt-2 text-sm text-amber-700" role="status">
          Informe um e-mail válido para liberar o formulário de pagamento.
        </p>
      ) : null}
    </div>
  );
}
