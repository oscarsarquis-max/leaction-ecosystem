'use client'

import MediaPlayer from '@/components/MediaPlayer'
import ScormH5pFrame from '@/components/ScormH5pFrame'

const DEMO_OVERLAYS = [
  {
    id: 'cue-1',
    atSec: 30,
    type: 'mcq' as const,
    text: 'Qual é o objetivo desta lição?',
    choices: ['Memorizar slides', 'Aplicar o conceito', 'Pular o vídeo'],
  },
  {
    id: 'cue-2',
    atSec: 90,
    type: 'note' as const,
    text: 'Anote um exemplo do seu contexto de trabalho.',
  },
]

export default function PlayerDemoPage() {
  return (
    <main className="mx-auto max-w-3xl space-y-10 px-4 py-10">
      <header>
        <h1 className="text-2xl font-semibold">Demo — Player + overlays</h1>
        <p className="text-sm text-zinc-400">YouTube nocookie · camadas interativas · SCORM iframe</p>
      </header>

      <section>
        <h2 className="mb-3 text-lg">Vídeo</h2>
        <MediaPlayer
          mediaUrl="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
          title="Demo LEACTIONA"
          lessonId="demo-lesson"
          overlays={DEMO_OVERLAYS}
          onCompleted={() => {
            // Em produção: reportVideoCompleted + DPoP
            console.info('[demo] video completed — xAPI via API')
          }}
        />
      </section>

      <section>
        <h2 className="mb-3 text-lg">Pacote SCORM/H5P</h2>
        <ScormH5pFrame
          kind="SCORM"
          title="Pacote demo"
          packageUrl="about:blank"
        />
      </section>
    </main>
  )
}
