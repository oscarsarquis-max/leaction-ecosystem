/** Detecção de ambiente para ditado — Chrome Android, Safari iOS, desktop. */

export function getSpeechEnvironment() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return {
      speechSupported: false,
      isIOS: false,
      isAndroid: false,
      isSafari: false,
      isMobile: false,
      useContinuous: true,
      platformLabel: 'navegador',
    };
  }

  const ua = navigator.userAgent || '';
  const isIOS =
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const isAndroid = /Android/i.test(ua);
  const isSafari = /Safari/i.test(ua) && !/Chrome|CriOS|FxiOS|EdgiOS/i.test(ua);
  const isMobile = isIOS || isAndroid || /Mobi/i.test(ua);

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const speechSupported = !!SpeechRecognition;

  let platformLabel = 'Chrome ou Edge';
  if (isIOS && isSafari) platformLabel = 'Safari (iPhone/iPad)';
  else if (isIOS) platformLabel = 'Chrome no iPhone';
  else if (isAndroid) platformLabel = 'Chrome no Android';

  return {
    speechSupported,
    isIOS,
    isAndroid,
    isSafari,
    isMobile,
    /** iOS Safari: continuous=false + reinício manual é mais estável */
    useContinuous: !isIOS,
    platformLabel,
  };
}

export function dictationHelpText(env) {
  if (!env.speechSupported) {
    if (env.isIOS && !env.isSafari) {
      return 'No iPhone, use o Safari ou o Chrome para ditado por voz. Você também pode digitar normalmente.';
    }
    if (env.isIOS) {
      return 'Atualize o iOS (14.5+) e permita reconhecimento de fala nas configurações do Safari. Ou digite manualmente.';
    }
    return 'Ditado indisponível neste navegador. Digite manualmente ou use Chrome/Safari no celular.';
  }
  if (env.isIOS) {
    return 'No iPhone: toque em Ditado, permita microfone e fala. Toque em Parar ou diga «fim». Pode ser necessário tocar Ditado de novo após pausas longas.';
  }
  if (env.isMobile) {
    return 'Toque em Ditado, permita o microfone e fale. Toque em Parar ou diga «fim» para encerrar.';
  }
  return 'Clique em Ditado ou diga «fim» para encerrar a gravação.';
}
