import { useCallback, useEffect, useState } from 'react';

type MicState = 'unknown' | 'granted' | 'denied' | 'prompt';

function speechSupported() {
  if (typeof window === 'undefined') return false;
  const w = window as Window & { webkitSpeechRecognition?: unknown; SpeechRecognition?: unknown };
  return Boolean(w.SpeechRecognition || w.webkitSpeechRecognition);
}

export function useMicPermissionBanner() {
  const [micState, setMicState] = useState<MicState>('unknown');
  const [dismissed, setDismissed] = useState(false);
  const [activating, setActivating] = useState(false);
  const supported = speechSupported();

  useEffect(() => {
    if (!supported || !navigator.permissions?.query) return;
    let cancelled = false;
    navigator.permissions
      .query({ name: 'microphone' as PermissionName })
      .then((status) => {
        if (cancelled) return;
        setMicState(status.state as MicState);
        status.onchange = () => setMicState(status.state as MicState);
      })
      .catch(() => setMicState('prompt'));
    return () => {
      cancelled = true;
    };
  }, [supported]);

  const activateMic = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicState('denied');
      return;
    }
    setActivating(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setMicState('granted');
      setDismissed(true);
    } catch {
      setMicState('denied');
    } finally {
      setActivating(false);
    }
  }, []);

  const visible =
    supported &&
    micState !== 'granted' &&
    micState !== 'unknown' &&
    (micState === 'denied' || !dismissed);

  return {
    visible,
    micState,
    activating,
    activateMic,
    dismiss: () => setDismissed(true),
  };
}
