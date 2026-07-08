/** Abre exatamente uma aba externa por gesto — mutex global + anchor programático. */
let openingUntil = 0;

export function openExternalUrl(url: string): boolean {
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    return false;
  }

  const now = Date.now();
  if (now < openingUntil) {
    return false;
  }
  openingUntil = now + 2000;

  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.target = '_blank';
  anchor.rel = 'noopener noreferrer';
  anchor.referrerPolicy = 'no-referrer';
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  return true;
}
