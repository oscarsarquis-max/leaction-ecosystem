import { useCallback, useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
  if (typeof window === 'undefined') return null
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function joinSpeech(base, chunk, { preserveNewlines = false } = {}) {
  const b = base || ''
  const c = String(chunk || '').trim()
  if (!c) return b
  const sep = !b ? '' : b.endsWith('\n') || b.endsWith(' ') ? '' : ' '
  const joined = `${b}${sep}${c}`
  if (preserveNewlines) {
    return joined.replace(/[^\S\n]+/g, ' ').replace(/ *\n */g, '\n')
  }
  return joined.replace(/\s+/g, ' ').trimStart()
}

/**
 * Ditado por microfone (Web Speech API · pt-BR).
 * Fica ativo até o usuário clicar para encerrar — pausas/respirações reiniciam sozinhas.
 *
 * @param {{ value: string, onChange: (next: string) => void, preserveNewlines?: boolean }} opts
 */
export function useSpeechDictation({ value, onChange, preserveNewlines = false }) {
  const [listening, setListening] = useState(false)
  const [supported, setSupported] = useState(true)
  const [error, setError] = useState('')

  const recognitionRef = useRef(null)
  const baseValueRef = useRef(value)
  const interimRef = useRef('')
  const wantListenRef = useRef(false)
  const restartTimerRef = useRef(null)
  const onChangeRef = useRef(onChange)
  const valueRef = useRef(value)
  const preserveRef = useRef(preserveNewlines)
  const beginSessionRef = useRef(() => {})

  onChangeRef.current = onChange
  valueRef.current = value
  preserveRef.current = preserveNewlines

  useEffect(() => {
    setSupported(Boolean(getSpeechRecognition()))
  }, [])

  useEffect(() => {
    if (!wantListenRef.current) {
      baseValueRef.current = value
    }
  }, [value])

  const clearRestartTimer = useCallback(() => {
    if (restartTimerRef.current != null) {
      window.clearTimeout(restartTimerRef.current)
      restartTimerRef.current = null
    }
  }, [])

  const commitInterimIfAny = useCallback(() => {
    const interim = (interimRef.current || '').trim()
    interimRef.current = ''
    if (!interim) return
    const next = joinSpeech(baseValueRef.current, interim, {
      preserveNewlines: preserveRef.current,
    })
    baseValueRef.current = next
    onChangeRef.current(next)
  }, [])

  const detachRecognition = useCallback(() => {
    const rec = recognitionRef.current
    recognitionRef.current = null
    if (!rec) return
    try {
      rec.onstart = null
      rec.onerror = null
      rec.onresult = null
      rec.onend = null
      rec.abort()
    } catch {
      try {
        rec.stop()
      } catch {
        /* ignore */
      }
    }
  }, [])

  const stop = useCallback(() => {
    wantListenRef.current = false
    clearRestartTimer()
    detachRecognition()
    commitInterimIfAny()
    setListening(false)
  }, [clearRestartTimer, commitInterimIfAny, detachRecognition])

  const beginSession = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition || !wantListenRef.current) return

    clearRestartTimer()
    detachRecognition()

    const rec = new SpeechRecognition()
    rec.lang = 'pt-BR'
    rec.continuous = true
    rec.interimResults = true
    rec.maxAlternatives = 1

    rec.onstart = () => {
      if (wantListenRef.current) setListening(true)
    }

    rec.onerror = (event) => {
      const code = event?.error || 'error'
      if (code === 'not-allowed' || code === 'service-not-allowed') {
        wantListenRef.current = false
        clearRestartTimer()
        setError(
          'Permissão de microfone negada. Libere o acesso nas configurações do navegador.',
        )
        setListening(false)
        return
      }
      if (code === 'audio-capture') {
        wantListenRef.current = false
        clearRestartTimer()
        setError('Não foi possível acessar o microfone.')
        setListening(false)
        return
      }
      // no-speech / aborted / network: mantem ativo; onend reinicia
      if (code === 'no-speech' || code === 'aborted' || code === 'network') {
        setError('')
      }
    }

    rec.onresult = (event) => {
      if (!wantListenRef.current) return

      let finalChunk = ''
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        const transcript = result[0]?.transcript || ''
        if (result.isFinal) finalChunk += transcript
        else interim += transcript
      }

      if (finalChunk) {
        interimRef.current = ''
        const next = joinSpeech(baseValueRef.current, finalChunk, {
          preserveNewlines: preserveRef.current,
        })
        baseValueRef.current = next
        if (interim) {
          interimRef.current = interim
          onChangeRef.current(
            joinSpeech(next, interim, { preserveNewlines: preserveRef.current }),
          )
        } else {
          onChangeRef.current(next)
        }
        return
      }

      if (interim) {
        interimRef.current = interim
        onChangeRef.current(
          joinSpeech(baseValueRef.current, interim, {
            preserveNewlines: preserveRef.current,
          }),
        )
      }
    }

    rec.onend = () => {
      recognitionRef.current = null
      if (!wantListenRef.current) {
        commitInterimIfAny()
        setListening(false)
        return
      }
      // Respiração/silêncio: confirma texto e reabre imediatamente
      commitInterimIfAny()
      setListening(true)
      clearRestartTimer()
      restartTimerRef.current = window.setTimeout(() => {
        if (wantListenRef.current) beginSessionRef.current()
      }, 60)
    }

    recognitionRef.current = rec
    try {
      rec.start()
      setListening(true)
    } catch {
      if (wantListenRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (wantListenRef.current) beginSessionRef.current()
        }, 200)
      }
    }
  }, [clearRestartTimer, commitInterimIfAny, detachRecognition])

  beginSessionRef.current = beginSession

  const start = useCallback(() => {
    if (!getSpeechRecognition()) {
      setSupported(false)
      setError('Seu navegador não suporta ditado por voz. Use Chrome ou Edge.')
      return
    }

    setError('')
    wantListenRef.current = true
    baseValueRef.current = valueRef.current || ''
    interimRef.current = ''
    setListening(true)
    beginSession()
  }, [beginSession])

  const toggle = useCallback(() => {
    if (wantListenRef.current || listening) stop()
    else start()
  }, [listening, start, stop])

  useEffect(() => () => stop(), [stop])

  return { listening, supported, error, start, stop, toggle, setError }
}

/**
 * Campo de texto/textarea com botão de ditado.
 * O microfone só para quando o usuário clica de novo.
 */
export default function DictationField({
  as = 'input',
  value,
  onChange,
  className = 'field-input',
  continuous: _continuous,
  ...rest
}) {
  const isTextarea = as === 'textarea'
  const { listening, supported, error, toggle, setError } = useSpeechDictation({
    value: value || '',
    onChange,
    preserveNewlines: isTextarea,
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
        <p className="text-[11px] font-semibold text-brand-600">
          Ouvindo… continue falando. Clique no microfone para encerrar.
        </p>
      ) : null}
      {error ? <p className="text-[11px] text-bordo">{error}</p> : null}
    </div>
  )
}
