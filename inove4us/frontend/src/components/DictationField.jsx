import { useCallback, useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

/**
 * Ditado por microfone (Web Speech API · pt-BR).
 * @param {{ value: string, onChange: (next: string) => void, continuous?: boolean }} opts
 */
export function useSpeechDictation({ value, onChange, continuous = true }) {
  const [listening, setListening] = useState(false)
  const [supported, setSupported] = useState(true)
  const [error, setError] = useState('')
  const recognitionRef = useRef(null)
  const baseValueRef = useRef(value)
  const interimRef = useRef('')

  useEffect(() => {
    setSupported(Boolean(getSpeechRecognition()))
  }, [])

  useEffect(() => {
    if (!listening) baseValueRef.current = value
  }, [value, listening])

  const stop = useCallback(() => {
    const rec = recognitionRef.current
    if (rec) {
      try {
        rec.onend = null
        rec.stop()
      } catch {
        /* ignore */
      }
      recognitionRef.current = null
    }
    interimRef.current = ''
    setListening(false)
  }, [])

  const start = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) {
      setSupported(false)
      setError('Seu navegador não suporta ditado por voz. Use Chrome ou Edge.')
      return
    }

    stop()
    setError('')
    baseValueRef.current = value
    interimRef.current = ''

    const rec = new SpeechRecognition()
    rec.lang = 'pt-BR'
    rec.continuous = continuous
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onstart = () => setListening(true)

    rec.onerror = (event) => {
      const code = event?.error || 'error'
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        setError('Permissão de microfone negada. Libere o acesso nas configurações do navegador.')
      } else if (code === 'no-speech') {
        setError('Não ouvi nada. Tente novamente.')
      } else if (code !== 'aborted') {
        setError('Falha no ditado. Tente de novo.')
      }
      setListening(false)
    }

    rec.onresult = (event) => {
      let finalChunk = ''
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        const transcript = result[0]?.transcript || ''
        if (result.isFinal) finalChunk += transcript
        else interim += transcript
      }

      if (finalChunk) {
        const base = baseValueRef.current || ''
        const sep = base && !base.endsWith(' ') && !base.endsWith('\n') ? ' ' : ''
        const next = `${base}${sep}${finalChunk.trim()}`.replace(/\s+/g, ' ').trimStart()
        baseValueRef.current = next
        interimRef.current = ''
        onChange(next)
      } else if (interim) {
        interimRef.current = interim
        const base = baseValueRef.current || ''
        const sep = base && !base.endsWith(' ') ? ' ' : ''
        onChange(`${base}${sep}${interim}`)
      }
    }

    rec.onend = () => {
      // Se parou no meio do continuous, não reinicia — usuário controla pelo botão
      recognitionRef.current = null
      setListening(false)
      // consolida valor final sem interim
      if (interimRef.current) {
        interimRef.current = ''
        onChange(baseValueRef.current || '')
      }
    }

    recognitionRef.current = rec
    try {
      rec.start()
    } catch {
      setError('Não foi possível iniciar o microfone.')
      setListening(false)
    }
  }, [continuous, onChange, stop, value])

  const toggle = useCallback(() => {
    if (listening) stop()
    else start()
  }, [listening, start, stop])

  useEffect(() => () => stop(), [stop])

  return { listening, supported, error, start, stop, toggle, setError }
}

/**
 * Campo de texto/textarea com botão de ditado.
 */
export default function DictationField({
  as = 'input',
  value,
  onChange,
  className = 'field-input',
  continuous,
  ...rest
}) {
  const isTextarea = as === 'textarea'
  const { listening, supported, error, toggle, setError } = useSpeechDictation({
    value: value || '',
    onChange,
    continuous: continuous ?? isTextarea,
  })

  const Tag = isTextarea ? 'textarea' : 'input'

  return (
    <div className="space-y-1.5">
      <div className="relative">
        <Tag
          {...rest}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${className} ${supported ? 'pr-12' : ''}`}
        />
        {supported ? (
          <button
            type="button"
            onClick={() => {
              setError('')
              toggle()
            }}
            title={listening ? 'Parar ditado' : 'Ditar por microfone'}
            aria-label={listening ? 'Parar ditado' : 'Ditar por microfone'}
            aria-pressed={listening}
            className={[
              'absolute right-2 flex h-9 w-9 items-center justify-center rounded-lg transition',
              isTextarea ? 'top-2.5' : 'top-1/2 -translate-y-1/2',
              listening
                ? 'bg-brand-600 text-white shadow-soft ring-2 ring-brand-200'
                : 'bg-brand-50 text-bordo hover:bg-brand-100',
            ].join(' ')}
          >
            {listening ? (
              <span className="relative flex h-3 w-3">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white/70" />
                <span className="relative inline-flex h-3 w-3 rounded-full bg-white" />
              </span>
            ) : (
              <i className="fa-solid fa-microphone text-sm" />
            )}
          </button>
        ) : null}
      </div>
      {listening ? (
        <p className="text-[11px] font-semibold text-brand-600">Ouvindo… fale agora</p>
      ) : null}
      {error ? <p className="text-[11px] text-bordo">{error}</p> : null}
    </div>
  )
}
