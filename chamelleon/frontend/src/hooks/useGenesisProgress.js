import { useCallback, useEffect, useRef, useState } from 'react';
import { getTdGenesisStatus } from '../services/tdApi';
import { GENESIS_STATUS_LABELS } from '../utils/genesisHints';

const POLL_MS = 2500;
const PROGRESS_MS = 400;
const HINT_MS = 4500;

function buildStatusMessage(statusIa, faseAtual) {
  const key = (statusIa || '').toUpperCase();
  let msg = GENESIS_STATUS_LABELS[key] || 'Processando seu plano de transformação…';
  if (faseAtual && key !== 'CONCLUIDO') {
    msg += ` (${faseAtual})`;
  }
  return msg;
}

export function useGenesisProgress({ hints = [], onComplete, onError } = {}) {
  const [active, setActive] = useState(false);
  const [progress, setProgress] = useState(8);
  const [statusMessage, setStatusMessage] = useState('');
  const [hintIndex, setHintIndex] = useState(0);
  const [subtitle, setSubtitle] = useState(
    'Aguardando conclusão do processamento. Os insights abaixo vêm do seu relatório de maturidade.',
  );

  const pollTimerRef = useRef(null);
  const progressTimerRef = useRef(null);
  const hintTimerRef = useRef(null);
  const startTimeRef = useRef(null);
  const generateRef = useRef(null);
  const finishedRef = useRef(false);

  const hintPool = hints.length > 0 ? hints : ['O Consultor LeAction está priorizando gaps do diagnóstico PanelDX.'];
  const currentHint = hintPool[hintIndex % hintPool.length];

  const stopTimers = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }
    if (hintTimerRef.current) {
      clearInterval(hintTimerRef.current);
      hintTimerRef.current = null;
    }
  }, []);

  const finishSuccess = useCallback(async () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    stopTimers();
    setProgress(100);
    setStatusMessage(GENESIS_STATUS_LABELS.CONCLUIDO);
    setSubtitle('Redirecionando para o Plano Diretor…');
    setTimeout(() => {
      setActive(false);
      onComplete?.();
    }, 900);
  }, [onComplete, stopTimers]);

  const finishError = useCallback(
    (message) => {
      if (finishedRef.current) return;
      finishedRef.current = true;
      stopTimers();
      setActive(false);
      onError?.(message || 'Falha na Gênese do plano de TD.');
    },
    [onError, stopTimers],
  );

  const pollOnce = useCallback(async () => {
    try {
      const data = await getTdGenesisStatus();
      if (!data) return;
      setStatusMessage(buildStatusMessage(data.status_ia, data.fase_atual));
      if (data.erro) {
        finishError('O Consultor LeAction encontrou um erro ao gerar o plano. Tente novamente.');
        return;
      }
      if (data.plano_pronto) {
        await finishSuccess();
      }
    } catch {
      // Poll silencioso — POST principal ainda pode estar em andamento.
    }
  }, [finishError, finishSuccess]);

  const startTimers = useCallback(() => {
    startTimeRef.current = Date.now();
    progressTimerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      const target = Math.min(88, 12 + elapsed * 1.8);
      setProgress(target);
    }, PROGRESS_MS);

    hintTimerRef.current = setInterval(() => {
      setHintIndex((prev) => prev + 1);
    }, HINT_MS);

    pollOnce();
    pollTimerRef.current = setInterval(pollOnce, POLL_MS);
  }, [pollOnce]);

  const start = useCallback(
    (runGenerate) => {
      finishedRef.current = false;
      generateRef.current = runGenerate;
      setActive(true);
      setProgress(8);
      setHintIndex(0);
      setStatusMessage(buildStatusMessage('PENDENTE', ''));
      setSubtitle(
        'Aguardando conclusão do processamento. Os insights abaixo vêm do seu relatório de maturidade.',
      );
      startTimers();

      Promise.resolve()
        .then(() => runGenerate?.())
        .then(() => pollOnce())
        .catch((err) => {
          finishError(err?.message || 'Falha ao gerar o plano de TD.');
        });
    },
    [finishError, pollOnce, startTimers],
  );

  const resume = useCallback(() => {
    if (active || finishedRef.current) return;
    finishedRef.current = false;
    setActive(true);
    setProgress(12);
    setStatusMessage(buildStatusMessage('PROCESSANDO', ''));
    startTimers();
  }, [active, startTimers]);

  useEffect(() => () => stopTimers(), [stopTimers]);

  return {
    active,
    progress,
    statusMessage,
    subtitle,
    currentHint,
    hintCount: hintPool.length,
    hintIndex: hintIndex % hintPool.length,
    start,
    resume,
    stop: () => {
      finishedRef.current = true;
      stopTimers();
      setActive(false);
    },
  };
}
