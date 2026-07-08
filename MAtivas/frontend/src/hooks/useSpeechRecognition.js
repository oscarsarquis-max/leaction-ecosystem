import { useCallback, useEffect, useRef, useState } from 'react'

const SpeechRecognition =
  typeof window !== 'undefined'
    ? window.SpeechRecognition || window.webkitSpeechRecognition
    : null

function mapSpeechError(event) {
  switch (event.error) {
    case 'not-allowed':
    case 'service-not-allowed':
      return 'Permissão do microfone negada. Verifique as configurações do navegador.'
    case 'audio-capture':
      return 'Não foi possível acessar o microfone. Verifique se ele está conectado.'
    case 'network':
      return 'Erro de rede ao transcrever a fala. Tente novamente.'
    case 'no-speech':
      return null
    case 'aborted':
      return null
    default:
      return 'Não foi possível transcrever a fala. Tente novamente.'
  }
}

/**
 * Reconhecimento de voz via Web Speech API (Chrome, Edge, Safari).
 * Em produção, o microfone exige HTTPS (exceto localhost).
 */
export function useSpeechRecognition({ onResult, lang = 'pt-BR', maxChars = 800 } = {}) {
  const [listening, setListening] = useState(false)
  const [error, setError] = useState(null)
  const supported = Boolean(SpeechRecognition)

  const recognitionRef = useRef(null)
  const listeningRef = useRef(false)
  const baseTextRef = useRef('')
  const finalTranscriptRef = useRef('')

  const stop = useCallback(() => {
    listeningRef.current = false
    setListening(false)
    const rec = recognitionRef.current
    recognitionRef.current = null
    try {
      rec?.abort()
    } catch {
      /* ignora falha ao encerrar */
    }
  }, [])

  const start = useCallback(
    (baseText = '') => {
      if (!SpeechRecognition) {
        setError('Seu navegador não suporta transcrição por voz. Use Chrome, Edge ou Safari.')
        return
      }

      if (!window.isSecureContext) {
        setError(
          'O microfone só funciona em conexão segura (HTTPS). Acesse o site com https://.',
        )
        return
      }

      setError(null)
      baseTextRef.current = baseText
      finalTranscriptRef.current = ''
      listeningRef.current = true
      setListening(true)

      const recognition = new SpeechRecognition()
      recognition.lang = lang
      recognition.continuous = true
      recognition.interimResults = true

      recognition.onresult = (event) => {
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const chunk = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscriptRef.current += chunk
          } else {
            interim += chunk
          }
        }

        const prefix = baseTextRef.current
        const separator =
          prefix && (finalTranscriptRef.current || interim) && !prefix.endsWith(' ')
            ? ' '
            : ''
        const combined = `${prefix}${separator}${finalTranscriptRef.current}${interim}`.trim()
        onResult?.(combined.slice(0, maxChars))
      }

      recognition.onerror = (event) => {
        const message = mapSpeechError(event)
        if (message) {
          setError(message)
          stop()
        }
      }

      recognition.onend = () => {
        if (listeningRef.current) {
          try {
            recognition.start()
          } catch {
            listeningRef.current = false
            setListening(false)
          }
        }
      }

      recognitionRef.current = recognition

      try {
        recognition.start()
      } catch {
        setError('Não foi possível iniciar o microfone. Tente novamente.')
        listeningRef.current = false
        setListening(false)
      }
    },
    [lang, maxChars, onResult, stop],
  )

  const toggle = useCallback(
    (baseText = '') => {
      if (listeningRef.current) {
        stop()
      } else {
        start(baseText)
      }
    },
    [start, stop],
  )

  useEffect(() => () => {
    listeningRef.current = false
    try {
      recognitionRef.current?.abort()
    } catch {
      /* noop */
    }
    recognitionRef.current = null
  }, [])

  return { supported, listening, error, toggle, stop, reset: stop }
}
