import { LogOut } from 'lucide-react'
import CrystalBallPanel from '../components/CrystalBallPanel'
import { useAuth } from './AuthContext'

/**
 * Shell enxuto para restricted_tester — só Simulação Mativas.
 */
export default function RestrictedShell({ apiBase }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-gradient-to-b from-teal-50 to-slate-100">
      <header className="border-b border-teal-200 bg-white/80 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2">
          <div>
            <p className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
              Phanton · Simulação
            </p>
            <p className="text-sm text-slate-600">
              Olá, <span className="font-semibold">{user?.username}</span> ·
              acesso restrito (Mativas)
            </p>
          </div>
          <button
            type="button"
            onClick={async () => {
              await logout()
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sair
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <CrystalBallPanel
          apiBase={apiBase}
          activeRunId={null}
          onError={() => {}}
          mode="restricted"
        />
      </main>
    </div>
  )
}
