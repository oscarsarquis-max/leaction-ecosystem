/**
 * Ditado por voz (Web Speech API) — port React do PanelDX voz-ditado.js
 * Parar: botão «Parar», clique no mic ou diga «fim».
 */
import { useCallback, useEffect, useRef, useState } from 'react';

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

export function useSpeechDictation({ onValueChange, onError } = {}) {
  const [status, setStatus] = useState('');
  const [activeFieldId, setActiveFieldId] = useState(null);
  const [isListening, setIsListening] = useState(false);

  const sessionRef = useRef({
    sessionAtiva: false,
    paradaManual: false,
    recebeu: false,
    campoAlvoId: null,
    valorBase: '',
    transcricaoSessao: '',
    motor: null,
    reiniciosSessao: 0,
    iniciandoMotor: false,
    restartTimer: null,
    startTimer: null,
  });

  const limparTimers = useCallback(() => {
    const s = sessionRef.current;
    if (s.restartTimer) {
      clearTimeout(s.restartTimer);
      s.restartTimer = null;
    }
    if (s.startTimer) {
      clearTimeout(s.startTimer);
      s.startTimer = null;
    }
  }, []);

  const pararMotor = useCallback(() => {
    const s = sessionRef.current;
    if (!s.motor) return;
    const m = s.motor;
    s.motor = null;
    m.onstart = null;
    m.onresult = null;
    m.onerror = null;
    m.onend = null;
    m.onspeechstart = null;
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
  }, []);

  const finalizarSessao = useCallback(
    (silencioso) => {
      limparTimers();
      const s = sessionRef.current;
      s.sessionAtiva = false;
      s.paradaManual = false;
      s.reiniciosSessao = 0;
      s.iniciandoMotor = false;
      s.campoAlvoId = null;
      s.valorBase = '';
      s.transcricaoSessao = '';
      setActiveFieldId(null);
      setIsListening(false);
      if (!silencioso) setStatus('');
    },
    [limparTimers],
  );

  const atualizarCampo = useCallback(
    (fieldId, interim, commitFinal) => {
      const s = sessionRef.current;
      const value = montarValorCampo(s.valorBase, s.transcricaoSessao, interim || '');
      onValueChange?.(fieldId, value, commitFinal);
    },
    [onValueChange],
  );

  const parar = useCallback(
    (silencioso, motivo) => {
      const s = sessionRef.current;
      s.paradaManual = true;
      s.sessionAtiva = false;
      limparTimers();
      pararMotor();
      const recebeu = s.recebeu;
      s.recebeu = false;
      finalizarSessao(silencioso);
      if (!silencioso) {
        if (motivo === 'palavra-chave') {
          setStatus('Ditado encerrado — palavra «fim» reconhecida. Texto salvo.');
        } else {
          setStatus(recebeu ? 'Ditado encerrado — texto salvo.' : 'Ditado encerrado.');
        }
      }
    },
    [finalizarSessao, limparTimers, pararMotor],
  );

  const pararPorPalavraChave = useCallback(
    (fieldId, textoRestante) => {
      const s = sessionRef.current;
      if (textoRestante !== undefined) {
        s.transcricaoSessao = textoRestante;
        atualizarCampo(fieldId, '', true);
        s.recebeu = true;
      }
      parar(false, 'palavra-chave');
    },
    [atualizarCampo, parar],
  );

  const ingestirTexto = useCallback(
    (fieldId, texto, isFinal) => {
      const s = sessionRef.current;
      const parsed = processarParadaPorVoz(texto);
      if (parsed.stop) {
        const merged = s.transcricaoSessao
          ? `${s.transcricaoSessao}${parsed.texto ? ` ${parsed.texto}` : ''}`.trim()
          : parsed.texto;
        pararPorPalavraChave(fieldId, merged);
        return true;
      }
      if (!parsed.texto) return false;
      if (isFinal) {
        s.transcricaoSessao = s.transcricaoSessao
          ? `${s.transcricaoSessao} ${parsed.texto}`
          : parsed.texto;
        s.recebeu = true;
        atualizarCampo(fieldId, '', true);
        setStatus('Fale ou diga «fim» / clique em Parar ditado para encerrar.');
      } else {
        atualizarCampo(fieldId, parsed.texto, false);
      }
      return false;
    },
    [atualizarCampo, pararPorPalavraChave],
  );

  const agendarReinicio = useCallback(
    (delay, forcarNovoMotor, iniciarMotorNovo) => {
      const s = sessionRef.current;
      limparTimers();
      if (s.reiniciosSessao >= MAX_REINICIOS_SESSAO) {
        setStatus('Pausa técnica — clique em Ditado para continuar neste campo.');
        parar(false);
        return;
      }
      s.restartTimer = setTimeout(() => {
        if (!s.sessionAtiva || s.paradaManual || !s.campoAlvoId) return;
        s.reiniciosSessao += 1;
        iniciarMotorNovo(forcarNovoMotor);
      }, delay || 200);
    },
    [limparTimers, parar],
  );

  const criarMotor = useCallback(
    (fieldId, iniciarMotorNovo) => {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) return null;

      const s = sessionRef.current;
      const rec = new SpeechRecognition();
      rec.lang = 'pt-BR';
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      rec.onstart = () => {
        s.iniciandoMotor = false;
        setIsListening(true);
        setStatus('Gravando… Diga «fim» ou clique em Parar ditado quando terminar.');
      };

      rec.onspeechstart = () => setStatus('Ouvindo você…');

      rec.onresult = (event) => {
        if (!s.sessionAtiva) return;
        let interim = '';
        let finalDelta = '';
        for (let i = event.resultIndex; i < event.results.length; i += 1) {
          const chunk = event.results[i][0]?.transcript || '';
          if (!chunk) continue;
          if (event.results[i].isFinal) finalDelta += chunk;
          else interim += chunk;
        }
        if (interim.trim() && ingestirTexto(fieldId, interim.trim(), false)) return;
        if (finalDelta.trim()) ingestirTexto(fieldId, finalDelta.trim(), true);
      };

      rec.onerror = (event) => {
        const err = event?.error || 'desconhecido';
        s.iniciandoMotor = false;
        if (err === 'not-allowed' || err === 'service-not-allowed') {
          onError?.('Permita o microfone no navegador e clique em Ditado novamente.');
          parar(true);
          return;
        }
        if (err === 'aborted') return;
        if (s.sessionAtiva && !s.paradaManual) {
          if (err === 'no-speech') {
            setStatus('Silêncio detectado — continue falando ou diga «fim».');
          } else {
            setStatus('Reconectando microfone…');
          }
          agendarReinicio(350, true, iniciarMotorNovo);
        }
      };

      rec.onend = () => {
        s.motor = null;
        s.iniciandoMotor = false;
        if (s.sessionAtiva && !s.paradaManual) {
          agendarReinicio(200, true, iniciarMotorNovo);
          return;
        }
        if (s.recebeu && !s.sessionAtiva) {
          setStatus('Texto salvo. Clique em Ditado para gravar outro trecho.');
        }
      };

      return rec;
    },
    [agendarReinicio, ingestirTexto, onError, parar],
  );

  const iniciarMotorNovo = useCallback(
    (forcarNovoMotor) => {
      const s = sessionRef.current;
      const fieldId = s.campoAlvoId;
      if (!s.sessionAtiva || s.paradaManual || !fieldId) return;
      if (s.iniciandoMotor) return;

      pararMotor();
      s.iniciandoMotor = true;

      const run = () => {
        if (!s.sessionAtiva || s.paradaManual) {
          s.iniciandoMotor = false;
          return;
        }
        if (forcarNovoMotor || !s.motor) {
          s.motor = criarMotor(fieldId, iniciarMotorNovo);
        }
        if (!s.motor) {
          s.iniciandoMotor = false;
          onError?.('Ditado indisponível neste navegador. Use Chrome ou Edge.');
          parar(true);
          return;
        }
        try {
          s.motor.start();
        } catch {
          s.iniciandoMotor = false;
          agendarReinicio(400, true, iniciarMotorNovo);
        }
      };

      s.startTimer = setTimeout(run, 280);
    },
    [agendarReinicio, criarMotor, onError, parar, pararMotor],
  );

  const toggleDictation = useCallback(
    (fieldId, currentValue) => {
      const s = sessionRef.current;
      if (s.sessionAtiva && s.campoAlvoId === fieldId) {
        parar(false);
        return;
      }
      if (s.sessionAtiva) parar(true);

      s.campoAlvoId = fieldId;
      s.valorBase = currentValue || '';
      s.transcricaoSessao = '';
      s.recebeu = false;
      s.paradaManual = false;
      s.sessionAtiva = true;
      s.reiniciosSessao = 0;
      setActiveFieldId(fieldId);
      setStatus('Abrindo microfone…');
      iniciarMotorNovo(true);
    },
    [iniciarMotorNovo, parar],
  );

  const stopDictation = useCallback(() => {
    if (sessionRef.current.sessionAtiva) parar(false);
  }, [parar]);

  useEffect(
    () => () => {
      limparTimers();
      pararMotor();
    },
    [limparTimers, pararMotor],
  );

  return {
    status,
    activeFieldId,
    isListening,
    toggleDictation,
    stopDictation,
  };
}
