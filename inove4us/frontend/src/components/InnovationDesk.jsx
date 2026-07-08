import { useState } from 'react'

const STEPS = [
  {
    id: 'empatia',
    number: 1,
    title: 'Empatia',
    short: 'Entenda as pessoas',
    description:
      'Compreenda profundamente as pessoas e o contexto do problema antes de propor qualquer solução.',
    icon: PeopleIcon,
    iconBg: 'bg-brand-100 text-brand-600',
  },
  {
    id: 'definicao',
    number: 2,
    title: 'Definição',
    short: 'Delimite o desafio',
    description:
      'Sintetize os achados da pesquisa e delimite com clareza o desafio central a ser resolvido.',
    icon: TargetIcon,
    iconBg: 'bg-accent-100 text-accent-500',
  },
  {
    id: 'ideacao',
    number: 3,
    title: 'Ideação',
    short: 'Gere ideias',
    description:
      'Estimule o maior número de ideias possíveis, sem julgamentos, explorando diferentes caminhos.',
    icon: BulbIcon,
    iconBg: 'bg-sky-100 text-sky-600',
  },
  {
    id: 'prototipacao',
    number: 4,
    title: 'Prototipação',
    short: 'Materialize soluções',
    description:
      'Transforme as ideias em protótipos rápidos e tangíveis que possam ser experimentados.',
    icon: CubeIcon,
    iconBg: 'bg-emerald-100 text-emerald-600',
  },
  {
    id: 'teste',
    number: 5,
    title: 'Teste',
    short: 'Valide e itere',
    description:
      'Valide as soluções com usuários reais, colete feedback e itere para aprimorar o resultado.',
    icon: CheckIcon,
    iconBg: 'bg-violet-100 text-violet-600',
  },
]

export default function InnovationDesk() {
  const [activeStep, setActiveStep] = useState('empatia')
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      content:
        'Olá! Sou o Agente de Inovação inove4us. Escolha uma fase do roteiro e me conte sobre o seu desafio para começarmos.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentProjectId, setCurrentProjectId] = useState(null)

  const activeStepData = STEPS.find((s) => s.id === activeStep)

  async function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    const userMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/agent/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          methodology_id: 'design_thinking',
          current_step: activeStep,
          user_input: text,
          project_id: currentProjectId,
        }),
      })
      const data = await res.json()
      if (data.project_id != null) {
        setCurrentProjectId(data.project_id)
      }
      setMessages((prev) => [
        ...prev,
        { role: 'agent', content: data.response ?? 'Sem resposta do agente.' },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          content:
            'Não consegui falar com o servidor agora. Verifique se o backend está rodando em localhost:5000.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 via-white to-white text-slate-800">
      <Header />

      <main className="mx-auto max-w-6xl px-4 pb-16 pt-10 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Coluna esquerda: saudação + livro */}
          <section className="space-y-6 lg:col-span-5">
            <Greeting />
            <BookCard />
          </section>

          {/* Coluna direita: roteiro de inovação */}
          <section className="lg:col-span-7">
            <Roadmap
              steps={STEPS}
              activeStep={activeStep}
              onSelect={setActiveStep}
            />
          </section>
        </div>

        {/* Agente de IA */}
        <div className="mt-6">
          <AgentPanel
            stepData={activeStepData}
            messages={messages}
            input={input}
            loading={loading}
            onInputChange={setInput}
            onSend={handleSend}
          />
        </div>

        <BookBanner />
        <AuthorFooter />
      </main>
    </div>
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-200/70 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex flex-col leading-none">
          <span className="text-lg font-extrabold tracking-tight text-brand-800">
            inove<span className="text-accent-500">4us</span>
          </span>
          <span className="mt-1 text-[10px] font-semibold uppercase tracking-[0.25em] text-slate-400">
            Metodologias inov-ativas
          </span>
        </div>
        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-500 sm:flex">
          <a className="transition hover:text-brand-700" href="#">
            Projetos
          </a>
          <a className="transition hover:text-brand-700" href="#">
            Metodologia
          </a>
          <a className="transition hover:text-brand-700" href="#">
            Ajuda
          </a>
        </nav>
      </div>
    </header>
  )
}

function Greeting() {
  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wider text-accent-500">
        Olá, inovador(a).
      </p>
      <h1 className="mt-2 text-3xl font-extrabold leading-tight tracking-tight text-brand-800 sm:text-4xl">
        Sua trilha de{' '}
        <span className="text-accent-500">Design Thinking</span>
      </h1>
      <p className="mt-4 text-slate-500">
        Com base no desafio que você quer resolver, montamos um roteiro
        inspirado na metodologia <strong>Design Thinking</strong>, das{' '}
        <strong>Metodologias inov-ativas</strong> de Andrea Filatro.
      </p>
      <p className="mt-3 text-slate-500">
        Avance pelas cinco fases e converse com o agente de IA para promover
        mais empatia, criatividade e protagonismo no seu projeto.
      </p>
    </Card>
  )
}

function BookCard() {
  return (
    <Card className="flex items-center gap-5">
      <div className="flex h-28 w-20 flex-none flex-col justify-between rounded-md bg-gradient-to-br from-brand-700 to-brand-900 p-2 text-white shadow-md">
        <span className="text-[8px] font-medium leading-tight opacity-80">
          Andrea Filatro
        </span>
        <span className="text-[11px] font-extrabold leading-tight">
          metodologias{' '}
          <span className="text-accent-300">inov</span>-ativas
        </span>
        <span className="text-[7px] uppercase tracking-wider opacity-70">
          na educação
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand-600">
          Base teórica
        </p>
        <h3 className="mt-1 text-base font-bold text-slate-900">
          Metodologias inov-ativas na educação
        </h3>
        <p className="mt-1 text-sm text-slate-500">
          O roteiro deste agente foi baseado nas estratégias “Faça Fácil” do
          livro.
        </p>
      </div>
    </Card>
  )
}

function Roadmap({ steps, activeStep, onSelect }) {
  return (
    <Card className="bg-brand-50/60">
      <div className="mb-6 flex items-start gap-3">
        <span className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
          <ClipboardIcon className="h-6 w-6" />
        </span>
        <div>
          <h2 className="text-xl font-extrabold text-brand-800">
            Seu Roteiro de Inovação
          </h2>
          <p className="text-sm font-medium text-accent-500">
            Metodologia: Design Thinking
          </p>
        </div>
      </div>

      <ol className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon
          const isActive = step.id === activeStep
          return (
            <li key={step.id}>
              <button
                type="button"
                onClick={() => onSelect(step.id)}
                className={`group flex w-full items-center gap-4 rounded-2xl border bg-white p-4 text-left transition ${
                  isActive
                    ? 'border-brand-300 ring-2 ring-brand-200'
                    : 'border-slate-200 hover:border-brand-200 hover:shadow-sm'
                }`}
              >
                <span
                  className={`flex h-9 w-9 flex-none items-center justify-center rounded-lg text-sm font-extrabold ${
                    isActive
                      ? 'bg-brand-600 text-white'
                      : 'bg-brand-100 text-brand-700'
                  }`}
                >
                  {step.number}
                </span>
                <span
                  className={`flex h-12 w-12 flex-none items-center justify-center rounded-full ${step.iconBg}`}
                >
                  <Icon className="h-6 w-6" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="text-base font-bold text-slate-900">
                      {step.title}
                    </span>
                    {isActive && (
                      <span className="rounded-full bg-accent-500 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
                        Ativo
                      </span>
                    )}
                  </span>
                  <span className="mt-0.5 block text-sm text-slate-500">
                    {step.description}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </Card>
  )
}

function AgentPanel({
  stepData,
  messages,
  input,
  loading,
  onInputChange,
  onSend,
}) {
  return (
    <Card>
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-100 text-accent-500">
          <SparkIcon className="h-5 w-5" />
        </span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-accent-500">
            Converse com o agente
          </p>
          <h2 className="text-base font-bold text-slate-900">
            Fase ativa: {stepData?.title}
          </h2>
        </div>
      </div>

      <div className="mb-4 max-h-80 space-y-3 overflow-y-auto rounded-xl bg-slate-50 p-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                msg.role === 'user'
                  ? 'rounded-br-sm bg-brand-600 text-white'
                  : 'rounded-bl-sm bg-white text-slate-700'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-2 text-sm text-slate-400 shadow-sm">
              Pensando…
            </div>
          </div>
        )}
      </div>

      <form onSubmit={onSend} className="flex items-end gap-2">
        <textarea
          rows={2}
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          placeholder="Descreva seu desafio ou faça uma pergunta…"
          className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) onSend(e)
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendIcon className="h-5 w-5" />
        </button>
      </form>
    </Card>
  )
}

function BookBanner() {
  return (
    <div className="mt-6 flex flex-col items-center justify-between gap-4 rounded-2xl border border-accent-100 bg-accent-50 p-6 sm:flex-row">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-white text-accent-500 shadow-sm">
          <BookIcon className="h-5 w-5" />
        </span>
        <p className="text-sm text-slate-600">
          Este roteiro foi baseado nas estratégias do livro{' '}
          <strong className="text-accent-600">
            Metodologias inov-ativas na educação
          </strong>
          .
        </p>
      </div>
      <a
        href="https://www.andreafilatro.com.br"
        target="_blank"
        rel="noreferrer"
        className="inline-flex flex-none items-center gap-2 rounded-xl bg-accent-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-600"
      >
        <BookIcon className="h-4 w-4" />
        Conheça o livro
      </a>
    </div>
  )
}

function AuthorFooter() {
  return (
    <footer className="mt-10 flex flex-col items-center gap-2 border-t border-slate-200 pt-8 text-center">
      <span className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-100 text-brand-700">
        <PeopleIcon className="h-7 w-7" />
      </span>
      <p className="text-sm text-slate-500">Conteúdo baseado na obra de</p>
      <p className="text-base font-bold text-brand-800">Andrea Filatro</p>
      <a
        href="https://www.andreafilatro.com.br"
        target="_blank"
        rel="noreferrer"
        className="text-sm font-medium text-accent-500 transition hover:text-accent-600"
      >
        www.andreafilatro.com.br
      </a>
    </footer>
  )
}

function Card({ children, className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
    >
      {children}
    </div>
  )
}

/* ----------------------------- Ícones ---------------------------- */

function SparkIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2l1.8 5.6L19 9l-5.2 1.4L12 16l-1.8-5.6L5 9l5.2-1.4z" />
    </svg>
  )
}

function ClipboardIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 2h6a2 2 0 0 1 2 2H7a2 2 0 0 1 2-2z" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="M8 11h8M8 15h6" />
    </svg>
  )
}

function PeopleIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function TargetIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1" />
    </svg>
  )
}

function BulbIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 18h6" />
      <path d="M10 22h4" />
      <path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2v.3h6v-.3c0-.8.4-1.5 1-2A7 7 0 0 0 12 2z" />
    </svg>
  )
}

function CubeIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 7.5 12 2 3 7.5v9L12 22l9-5.5z" />
      <path d="M3 7.5 12 13l9-5.5" />
      <path d="M12 22V13" />
    </svg>
  )
}

function CheckIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </svg>
  )
}

function BookIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function SendIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m22 2-7 20-4-9-9-4z" />
      <path d="M22 2 11 13" />
    </svg>
  )
}
