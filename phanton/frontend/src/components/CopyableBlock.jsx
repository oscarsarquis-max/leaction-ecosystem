import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

async function copyText(text) {
  if (navigator?.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  // Fallback para contextos sem Clipboard API
  const el = document.createElement('textarea')
  el.value = text
  el.setAttribute('readonly', '')
  el.style.position = 'fixed'
  el.style.left = '-9999px'
  document.body.appendChild(el)
  el.select()
  document.execCommand('copy')
  document.body.removeChild(el)
}

export default function CopyableBlock({
  text,
  label = 'Copiar',
  children,
  className = '',
  buttonClassName = '',
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await copyText(text ?? '')
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className={className}>
      {children}
      <div className="mt-2 flex justify-end">
        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
            copied
              ? 'border-emerald-400 bg-emerald-50 text-emerald-700'
              : 'border-slate-300 bg-white text-slate-600 hover:border-slate-400 hover:text-slate-900'
          } ${buttonClassName}`}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" />
              Copiado
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              {label}
            </>
          )}
        </button>
      </div>
    </div>
  )
}
