import { useCallback, useEffect, useRef, useState } from 'react';

type SpeechRecognitionCtor = new () => SpeechRecognition;

function getRecognitionCtor(): SpeechRecognitionCtor | null {
  const w = window as Window & {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export function useVoiceDictation() {
  const [isListening, setIsListening] = useState(false);
  const [status, setStatus] = useState('');
  const motorRef = useRef<SpeechRecognition | null>(null);
  const supported = typeof window !== 'undefined' && !!getRecognitionCtor();

  const stop = useCallback(() => {
    const motor = motorRef.current;
    if (motor) {
      try {
        motor.stop();
      } catch {
        /* ignore */
      }
      motorRef.current = null;
    }
    setIsListening(false);
    setStatus('');
  }, []);

  useEffect(() => () => stop(), [stop]);

  const dictate = useCallback(
  async (currentValue: string, onResult: (text: string) => void) => {
      const Ctor = getRecognitionCtor();
      if (!Ctor) {
        setStatus('Ditado indisponível neste navegador.');
        return;
      }

      stop();
      const rec = new Ctor();
      motorRef.current = rec;
      rec.lang = 'pt-BR';
      rec.continuous = false;
      rec.interimResults = true;

      let sessionText = '';

      rec.onstart = () => {
        setIsListening(true);
        setStatus('Ouvindo… toque novamente para parar.');
      };

      rec.onresult = (event: SpeechRecognitionEvent) => {
        let interim = '';
        let finalChunk = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const chunk = event.results[i][0]?.transcript || '';
          if (event.results[i].isFinal) finalChunk += chunk;
          else interim += chunk;
        }
        if (finalChunk) sessionText = `${sessionText} ${finalChunk}`.trim();
        const merged = [currentValue, sessionText, interim].filter(Boolean).join(' ').trim();
        onResult(merged);
      };

      rec.onerror = () => setStatus('Erro no microfone. Permita o acesso e tente de novo.');
      rec.onend = () => {
        setIsListening(false);
        setStatus('');
        motorRef.current = null;
      };

      try {
        rec.start();
      } catch {
        setStatus('Toque no microfone novamente.');
        setIsListening(false);
      }
    },
    [stop],
  );

  return { supported, isListening, status, dictate, stop };
}
