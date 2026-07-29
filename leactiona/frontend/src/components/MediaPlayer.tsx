'use client'

import { useCallback, useMemo, useState } from 'react'
import { resolveEmbedSrc } from '@/lib/embed'
import type { OverlayCue } from '@/player/render-player'

type Props = {
  mediaUrl: string
  title: string
  lessonId: string
  overlays?: OverlayCue[]
  /** Chamado ao “concluir” (botão ou evento futuro do player API). */
  onCompleted?: (info: { lessonId: string; durationSec?: number }) => void
}

/**
 * Player leve: iframe YouTube/Vimeo privacy-enhanced + camada DOM interativa (H5P-like).
 */
export default function MediaPlayer({
  mediaUrl,
  title,
  lessonId,
  overlays = [],
  onCompleted,
}: Props) {
  const embed = useMemo(() => resolveEmbedSrc(mediaUrl), [mediaUrl])
  const [activeId, setActiveId] = useState<string | null>(null)
  const active = overlays.find((o) => o.id === activeId) ?? null

  const showCue = useCallback((cue: OverlayCue) => setActiveId(cue.id), [])
  const dismiss = useCallback(() => setActiveId(null), [])

  if (!embed) {
    return (
      <div className="rounded bg-zinc-900 p-4 text-sm text-zinc-300" data-testid="player-root">
        Mídia não suportada neste player.
      </div>
    )
  }

  return (
    <div className="space-y-3" data-testid="player-root" data-provider={embed.kind}>
      <div className="relative w-full overflow-hidden bg-black pt-[56.25%]">
        <iframe
          data-testid="player-iframe"
          data-provider={embed.kind}
          title={title}
          src={embed.src}
          allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          className="absolute inset-0 h-full w-full border-0"
        />
        {active ? (
          <div
            className="absolute inset-x-4 bottom-4 rounded-lg bg-black/85 p-4 text-white shadow-lg backdrop-blur-sm"
            data-testid="player-overlay"
            data-overlay-id={active.id}
            role="dialog"
            aria-live="polite"
          >
            <p className="mb-3 text-sm leading-relaxed">{active.text}</p>
            {active.type === 'mcq' && active.choices?.length ? (
              <ul className="mb-3 space-y-2">
                {active.choices.map((c, i) => (
                  <li key={i}>
                    <button
                      type="button"
                      className="w-full rounded border border-white/20 px-3 py-2 text-left text-sm hover:bg-white/10"
                      data-choice={i}
                      onClick={dismiss}
                    >
                      {c}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            <button
              type="button"
              className="text-xs underline opacity-80"
              onClick={dismiss}
            >
              Fechar
            </button>
          </div>
        ) : null}
      </div>

      {overlays.length > 0 ? (
        <div className="flex flex-wrap gap-2" data-testid="overlay-cues">
          {overlays.map((cue) => (
            <button
              key={cue.id}
              type="button"
              className="rounded bg-zinc-800 px-2 py-1 text-xs text-zinc-200"
              onClick={() => showCue(cue)}
            >
              @{cue.atSec}s · {cue.type}
            </button>
          ))}
        </div>
      ) : null}

      <button
        type="button"
        data-testid="mark-complete"
        className="rounded bg-emerald-700 px-3 py-2 text-sm text-white"
        onClick={() => onCompleted?.({ lessonId })}
      >
        Marcar vídeo como concluído
      </button>
    </div>
  )
}
