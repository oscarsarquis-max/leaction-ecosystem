/** Resolve URLs leves YouTube/Vimeo (privacy-enhanced, sem UI de anúncios/sugestões). */

export type EmbedKind = 'youtube' | 'vimeo' | 'unknown'

export function detectEmbedKind(url: string): EmbedKind {
  try {
    const u = new URL(url)
    if (u.hostname.includes('youtu')) return 'youtube'
    if (u.hostname.includes('vimeo')) return 'vimeo'
  } catch {
    /* ignore */
  }
  return 'unknown'
}

export function toYouTubeEmbedUrl(url: string): string | null {
  try {
    const u = new URL(url)
    let id = ''
    if (u.hostname.includes('youtu.be')) id = u.pathname.slice(1)
    else if (u.searchParams.get('v')) id = u.searchParams.get('v')!
    else {
      const m = u.pathname.match(/\/embed\/([^/]+)/)
      if (m) id = m[1]!
    }
    if (!id || !/^[\w-]{6,}$/.test(id)) return null
    // youtube-nocookie + controles mínimos (modestbranding, rel=0)
    const params = new URLSearchParams({
      rel: '0',
      modestbranding: '1',
      controls: '1',
      playsinline: '1',
      enablejsapi: '1',
    })
    return `https://www.youtube-nocookie.com/embed/${id}?${params}`
  } catch {
    return null
  }
}

export function toVimeoEmbedUrl(url: string): string | null {
  try {
    const u = new URL(url)
    const m = u.pathname.match(/\/(?:video\/)?(\d+)/)
    if (!m) return null
    const id = m[1]!
    const params = new URLSearchParams({
      title: '0',
      byline: '0',
      portrait: '0',
      dnt: '1',
    })
    return `https://player.vimeo.com/video/${id}?${params}`
  } catch {
    return null
  }
}

export function resolveEmbedSrc(mediaUrl: string): { kind: EmbedKind; src: string } | null {
  const kind = detectEmbedKind(mediaUrl)
  if (kind === 'youtube') {
    const src = toYouTubeEmbedUrl(mediaUrl)
    return src ? { kind, src } : null
  }
  if (kind === 'vimeo') {
    const src = toVimeoEmbedUrl(mediaUrl)
    return src ? { kind, src } : null
  }
  return null
}
