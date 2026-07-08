/**
 * Ditado por voz (Web Speech API) — padrão PanelDX, otimizado para mobile (Safari iOS + Chrome).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { dictationHelpText, getSpeechEnvironment } from '../utils/speechDevice';

const PARADA_RE = /\b(fim|finalizar|encerrar|parar ditado|parar o ditado|stop)\b/i;
const MAX_REINICIOS_SESSAO = 40;

function processarParadaPorVoz(texto) {
  if (!texto) return { stop: false, texto: '' };
  const raw = String(texto).trim();
  const match = raw.match(PARADA_RE);
  if (!match) return { stop: false, texto: raw };
  const idx = raw.toLowerCase().indexOf(match[1].toLowerCase());
  const antes = raw.slice(0, idx).trim().replace(/[,.\-–—;:\s]+$/g, '');
  return { stop: true, texto: antes };
}

function montarValorCampo(valorBase, transcricaoSessao, interim) {
  const base = (valorBase || '').trim();
  const sessao = (transcricaoSessao || '').trim();
  const pedaco = (sessao + (interim ? `${sessao ? ' ' : ''}${interim.trim()}` : '')).trim();
  if (!pedaco) return base;
  return base ? `${base} ${pedaco}` : pedaco;
}

export function useVoiceDictation({ onValueChange, disabled = false }) {
  const env = useMemo(() => getSpeechEnvironment(), []);

  const [status, setStatus] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [activeFieldId, setActiveFieldId] = useState(null);
  const [fieldHighlight, setFieldHighlight] = useState(null);

  const motorRef = useRef(null);
  const sessionRef = useRef({
    ativa: false,
    paradaManual: false,
    campoId: null,
    valorBase: '',
    transcricaoSessao: '',
    recebeu: false,
    reinicios: 0,
    iniciando: false,
  });
  const timersRef = useRef({ restart: null, start: null });
  const onValueChangeRef = useRef(onValueChange);

  useEffect(() => {
    onValueChangeRef.current = onValueChange;
  }, [onValueChange]);

  const limparTimers = useCallback(() => {
    if (timersRef.current.restart) {
      clearTimeout(timersRef.current.restart);
      timersRef.current.restart = null;
    }
    if (timersRef.current.start) {
      clearTimeout(timersRef.current.start);
      timersRef.current.start = null;
    }
  }, []);

  const pararMotor = useCallback(() => {
    const m = motorRef.current;
    if (!m) return;
    m.onstart = null;
    m.onresult = null;
    m.onerror = null;
    m.onend = null;
    m.onspeechstart = null;
    m.onspeechend = null;
    try {
      m.abort();
    } catch {
      /* ignore */
    }
    try {
      m.stop();
    } catch {
      /* ignore */
    }
    motorRef.current = null;
  }, []);

  const finalizarSessao = useCallback(
    (silencioso) => {
      limparTimers();
      sessionRef.current = {
        ativa: false,
        paradaManual: false,
        campoId: null,
        valorBase: '',
        transcricaoSessao: '',
        recebeu: false,
        reinicios: 0,
        iniciando: false,
      };
      setIsListening(false);
      setActiveFieldId(null);
      setFieldHighlight(null);
      if (!silencioso) setStatus('');
    },
    [limparTimers],
  );

  const parar = useCallback(
    (silencioso, motivo) => {
      const sess = sessionRef.current;
      sess.paradaManual = true;
      sess.ativa = false;
      limparTimers();
      pararMotor();
      const recebeu = sess.recebeu;
      finalizarSessao(silencioso);
      if (!silencioso) {
        if (motivo === 'palavra-chave') {
          setStatus('Ditado encerrado — «fim» reconhecido. Texto salvo.');
        } else {
          setStatus(recebeu ? 'Ditado encerrado — texto salvo.' : 'Ditado encerrado.');
        }
      }
    },
    [finalizarSessao, limparTimers, pararMotor],
  );

  const atualizarCampo = useCallback((campoId, interim, commitFinal) => {
    const sess = sessionRef.current;
    const valor = montarValorCampo(sess.valorBase, sess.transcricaoSessao, interim || '');
    onValueChangeRef.current?.(campoId, valor);
    if (commitFinal) {
      setFieldHighlight({ id: campoId, flash: true });
      setTimeout(() => setFieldHighlight(null), 450);
    }
  }, []);

  const ingestirTexto = useCallback(
    (texto, isFinal) => {
      const parsed = processarParadaPorVoz(texto);
      if (parsed.stop) {
        const sess = sessionRef.current;
        const merged = sess.transcricaoSessao
          ? `${sess.transcricaoSessao}${parsed.texto ? ` ${parsed.texto}` : ''}`.trim()
          : parsed.texto;
        sess.transcricaoSessao = merged;
        atualizarCampo(sess.campoId, '', true);
        sess.recebeu = true;
        parar(false, 'palavra-chave');
        return true;
      }
      if (!parsed.texto) return false;
      const sess = sessionRef.current;
      if (isFinal) {
        sess.transcricaoSessao = sess.transcricaoSessao
          ? `${sess.transcricaoSessao} ${parsed.texto}`
          : parsed.texto;
        sess.recebeu = true;
        atualizarCampo(sess.campoId, '', true);
        setStatus(
          env.isMobile
            ? 'Ouvindo… Toque em Parar ou diga «fim».'
            : 'Fale ou diga «fim» / clique em Parar ditado.',
        );
      } else {
        atualizarCampo(sess.campoId, parsed.texto, false);
      }
      return false;
    },
    [atualizarCampo, env.isMobile, parar],
  );

  const configurarMotor = useCallback(
    (rec) => {
      rec.lang = 'pt-BR';
      rec.continuous = env.useContinuous;
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      rec.onstart = () => {
        sessionRef.current.iniciando = false;
        setIsListening(true);
        setStatus(
          env.isMobile
            ? 'Gravando… Toque em Parar ou diga «fim».'
            : 'Gravando… Diga «fim» ou clique em Parar ditado.',
        );
      };

      rec.onspeechstart = () => setStatus(env.isMobile ? 'Ouvindo você…' : 'Ouvindo você…');

      rec.onresult = (event) => {
        const sess = sessionRef.current;
        if (!sess.ativa) return;

        let interim = '';
        let finalDelta = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const chunk = event.results[i][0]?.transcript || '';
          if (!chunk) continue;
          if (event.results[i].isFinal) finalDelta += chunk;
          else interim += chunk;
        }
        if (interim.trim() && ingestirTexto(interim.trim(), false)) return;
        if (finalDelta.trim()) ingestirTexto(finalDelta.trim(), true);
      };

      rec.onerror = (event) => {
        const err = event?.error || 'desconhecido';
        sessionRef.current.iniciando = false;

        if (err === 'not-allowed' || err === 'service-not-allowed') {
          setStatus(
            env.isIOS
              ? 'Permita Microfone e Reconhecimento de Fala em Ajustes → Safari → este site.'
              : 'Permita o microfone no navegador e toque em Ditado novamente.',
          );
          parar(true);
          return;
        }
        if (err === 'aborted') return;

        const sess = sessionRef.current;
        if (sess.ativa && !sess.paradaManual) {
          if (err === 'no-speech') {
            setStatus(env.isMobile ? 'Silêncio — continue falando ou toque Parar.' : 'Silêncio detectado — continue ou diga «fim».');
          } else {
            setStatus(env.isMobile ? 'Reconectando…' : 'Reconectando microfone…');
          }
        }
      };

      rec.onend = () => {
        motorRef.current = null;
        sessionRef.current.iniciando = false;
        const sess = sessionRef.current;

        if (sess.ativa && !sess.paradaManual) {
          if (sess.reinicios >= MAX_REINICIOS_SESSAO) {
            setStatus('Pausa — toque em Ditado para continuar neste campo.');
            parar(false);
            return;
          }
          sess.reinicios += 1;
          const delay = env.isIOS ? 250 : env.isAndroid ? 200 : 150;
          limparTimers();
          timersRef.current.restart = setTimeout(() => {
            if (!sess.ativa || sess.paradaManual) return;
            try {
              const SpeechRecognition =
                window.SpeechRecognition || window.webkitSpeechRecognition;
              if (!SpeechRecognition) return;
              const next = new SpeechRecognition();
              motorRef.current = next;
              configurarMotor(next);
              next.start();
            } catch {
              setStatus('Toque em Ditado para continuar gravando.');
              parar(false);
            }
          }, delay);
          return;
        }

        if (sess.recebeu && !sess.ativa) {
          setStatus('Texto salvo. Toque em Ditado para gravar outro trecho.');
        }
      };
    },
    [env.isAndroid, env.isIOS, env.isMobile, env.useContinuous, ingestirTexto, limparTimers, parar],
  );

  const iniciarMotor = useCallback(() => {
    const sess = sessionRef.current;
    if (!sess.ativa || sess.paradaManual || sess.iniciando) return;

    sess.iniciando = true;
    setStatus('Abrindo microfone…');

    const delay = env.isMobile ? 0 : 120;

    timersRef.current.start = setTimeout(() => {
      if (!sess.ativa || sess.paradaManual) {
        sess.iniciando = false;
        return;
      }

      if (motorRef.current) {
        pararMotor();
      }

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        sess.iniciando = false;
        setStatus(dictationHelpText(env));
        parar(true);
        return;
      }

      const rec = new SpeechRecognition();
      configurarMotor(rec);
      motorRef.current = rec;

      try {
        rec.start();
      } catch (e) {
        sess.iniciando = false;
        const msg = String(e);
        if (msg.includes('already started')) {
          setTimeout(() => {
            if (!sess.ativa || sess.paradaManual) return;
            try {
              rec.start();
            } catch {
              setStatus('Toque em Ditado novamente.');
            }
          }, 300);
        } else {
          setStatus('Toque em Ditado novamente e permita o microfone.');
        }
      }
    }, delay);
  }, [configurarMotor, env, parar, pararMotor]);

  const toggleDictation = useCallback(
    (fieldId, currentValue) => {
      if (disabled || !env.speechSupported) return;

      const sess = sessionRef.current;
      if (sess.ativa && sess.campoId === fieldId) {
        parar(false);
        return;
      }

      if (sess.ativa) parar(true);

      sess.campoId = fieldId;
      sess.valorBase = currentValue || '';
      sess.transcricaoSessao = '';
      sess.recebeu = false;
      sess.paradaManual = false;
      sess.ativa = true;
      sess.reinicios = 0;

      setActiveFieldId(fieldId);
      iniciarMotor();
    },
    [disabled, env.speechSupported, iniciarMotor, parar],
  );

  useEffect(
    () => () => {
      parar(true);
      pararMotor();
    },
    [parar, pararMotor],
  );

  return {
    status,
    isListening,
    activeFieldId,
    fieldHighlight,
    speechSupported: env.speechSupported,
    speechEnv: env,
    helpText: dictationHelpText(env),
    toggleDictation,
    stopDictation: () => parar(false),
  };
}
