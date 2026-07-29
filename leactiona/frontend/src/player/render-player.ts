/**
 * Markup do player (testável sem browser): iframe + camada interativa sobreposta.
 */
import { resolveEmbedSrc } from '../lib/embed.js'

export type OverlayCue = {
  id: string
  atSec: number
  type: 'mcq' | 'note'
  text: string
  choices?: string[]
}

export function renderMediaPlayerMarkup(opts: {
  mediaUrl: string
  title: string
  overlays?: OverlayCue[]
  activeOverlayId?: string | null
}): string {
  const embed = resolveEmbedSrc(opts.mediaUrl)
  if (!embed) {
    return `<div class="la-player la-player--unsupported" data-testid="player-root">Mídia não suportada</div>`
  }

  const title = escapeHtml(opts.title)
  const iframe = [
    `<iframe`,
    ` data-testid="player-iframe"`,
    ` data-provider="${embed.kind}"`,
    ` title="${title}"`,
    ` src="${escapeAttr(embed.src)}"`,
    ` allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"`,
    ` allowfullscreen`,
    ` loading="lazy"`,
    ` referrerpolicy="strict-origin-when-cross-origin"`,
    ` style="position:absolute;inset:0;width:100%;height:100%;border:0;"`,
    `></iframe>`,
  ].join('')

  const active = opts.overlays?.find((o) => o.id === opts.activeOverlayId)
  const overlayHtml = active
    ? [
        `<div class="la-overlay" data-testid="player-overlay" data-overlay-id="${escapeAttr(active.id)}" role="dialog" aria-live="polite">`,
        `<p class="la-overlay__text">${escapeHtml(active.text)}</p>`,
        active.type === 'mcq' && active.choices?.length
          ? `<ul class="la-overlay__choices">${active.choices
              .map(
                (c, i) =>
                  `<li><button type="button" data-choice="${i}">${escapeHtml(c)}</button></li>`,
              )
              .join('')}</ul>`
          : '',
        `</div>`,
      ].join('')
    : ''

  return [
    `<div class="la-player" data-testid="player-root" data-provider="${embed.kind}" style="position:relative;padding-top:56.25%;background:#0b0b0b;overflow:hidden;">`,
    iframe,
    overlayHtml,
    `</div>`,
  ].join('')
}

export function renderScormH5pMarkup(opts: {
  packageUrl: string
  kind: 'SCORM' | 'H5P'
  title: string
}): string {
  return [
    `<div class="la-scorm" data-testid="scorm-root" data-kind="${opts.kind}" style="position:relative;min-height:480px;">`,
    `<iframe`,
    ` data-testid="scorm-iframe"`,
    ` title="${escapeAttr(opts.title)}"`,
    ` src="${escapeAttr(opts.packageUrl)}"`,
    ` sandbox="allow-scripts allow-same-origin allow-forms"`,
    ` style="width:100%;height:480px;border:0;"`,
    `></iframe>`,
    `</div>`,
  ].join('')
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function escapeAttr(s: string): string {
  return escapeHtml(s).replace(/'/g, '&#39;')
}
