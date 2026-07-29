import Link from 'next/link'

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">LEACTIONA</h1>
      <p className="mt-3 text-zinc-400">
        LMS multimídia single-tenant — player YouTube/Vimeo, SCORM/H5P e xAPI (Learning Locker).
      </p>
      <Link
        href="/demo/player/"
        className="mt-8 inline-block rounded bg-emerald-700 px-4 py-2 text-sm text-white"
      >
        Demo do player
      </Link>
    </main>
  )
}
