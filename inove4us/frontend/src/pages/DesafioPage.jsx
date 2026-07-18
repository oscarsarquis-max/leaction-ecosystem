import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import FloatingDictation from '../components/FloatingDictation'
import UpgradeCreditsModal from '../components/UpgradeCreditsModal'
import ProgressStepper from '../components/wizard/ProgressStepper'
import StepProblema from '../components/wizard/StepProblema'
import StepEstruturacao from '../components/wizard/StepEstruturacao'
import StepHipoteses from '../components/wizard/StepHipoteses'
import StepEduScrum from '../components/wizard/StepEduScrum'

function newSessionKey() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  return `aula-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

/**
 * Fluxo de investigação do problema → plano EduScrum (página própria).
 */
export default function DesafioPage() {
  const { user, logout } = useAuth()

  const [currentStep, setCurrentStep] = useState(1)
  const [problema, setProblema] = useState('')
  const [contexto, setContexto] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadingIa, setLoadingIa] = useState(false)

  const [causas, setCausas] = useState([])
  const [caminhos, setCaminhos] = useState([])
  const [referencial, setReferencial] = useState(null)
  const [fallback, setFallback] = useState(false)
  const [selectedCaminho, setSelectedCaminho] = useState(null)
  const [hipotese, setHipotese] = useState('')
  const [plano, setPlano] = useState(null)
  const [planoSession, setPlanoSession] = useState(null)
  const [ditadoLivre, setDitadoLivre] = useState('')
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)

  async function handleEstruturar() {
    setError('')
    setBusy(true)
    setLoadingIa(true)
    setCurrentStep(2)
    setSelectedCaminho(null)
    setHipotese('')
    setPlano(null)
    setPlanoSession(null)
    try {
      const data = await api.estruturarWizard({
        problema: problema.trim(),
        contexto: contexto.trim(),
        id_clie: user?.id_clie,
      })
      setCausas(data.causas_raiz || [])
      setCaminhos(data.caminhos || [])
      setReferencial(data.referencial || null)
      setFallback(Boolean(data.fallback))
    } catch (err) {
      setCurrentStep(1)
      const code = err?.code || err?.data?.code
      if (err?.status === 403 && code === 'INSUFFICIENT_CREDITS') {
        setError('')
        setShowUpgradeModal(true)
        return
      }
      setError(err.message || 'Não foi possível estruturar o problema.')
    } finally {
      setBusy(false)
      setLoadingIa(false)
    }
  }

  function handleSelectCaminho(caminho) {
    setSelectedCaminho(caminho)
    setHipotese(caminho?.hipotese_teste || '')
  }

  async function handleGerarPlano() {
    if (!selectedCaminho) return
    setBusy(true)
    const sessionKey = newSessionKey()
    try {
      const data = await api.selecionarCaminho(selectedCaminho)
      setHipotese(data.hipotese_teste || selectedCaminho.hipotese_teste)
      setPlano(data.plano_eduscrum || selectedCaminho.plano_eduscrum)
      setPlanoSession(sessionKey)
      setCurrentStep(4)
    } catch (err) {
      setHipotese(selectedCaminho.hipotese_teste)
      setPlano(selectedCaminho.plano_eduscrum)
      setPlanoSession(sessionKey)
      setCurrentStep(4)
      console.warn(err)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen">
      <ProgressStepper currentStep={currentStep} />

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <Link to="/mesa-do-inovador" className="btn-ghost !px-3 !py-1.5 text-xs">
            ← Início
          </Link>
          <p className="truncate text-sm text-bordo-soft">
            Desafio · <span className="font-semibold text-bordo">{user?.nome_clie || 'professor'}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {user?.creditos_ia != null ? (
            <span className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-bordo">
              {Number(user.creditos_ia)} créditos
            </span>
          ) : null}
          <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
            Sair
          </button>
        </div>
      </div>

      <main className="px-4 pb-16 pt-2 sm:px-6">
        {currentStep === 1 && (
          <StepProblema
            problema={problema}
            contexto={contexto}
            onProblemaChange={setProblema}
            onContextoChange={setContexto}
            onSubmit={handleEstruturar}
            busy={busy}
            error={error}
          />
        )}

        {currentStep === 2 && (
          <StepEstruturacao
            loading={loadingIa}
            causas={causas}
            referencial={referencial}
            fallback={fallback}
            onNext={() => setCurrentStep(3)}
          />
        )}

        {currentStep === 3 && (
          <StepHipoteses
            caminhos={caminhos}
            selectedId={selectedCaminho?.id}
            onSelect={handleSelectCaminho}
            hipotese={hipotese}
            onGerarPlano={handleGerarPlano}
            busy={busy}
          />
        )}

        {currentStep === 4 && plano && (
          <StepEduScrum
            plano={plano}
            hipotese={hipotese}
            problema={problema}
            user={user}
            planoSession={planoSession}
            onVoltar={() => setCurrentStep(3)}
          />
        )}
      </main>

      <FloatingDictation
        value={ditadoLivre}
        onChange={setDitadoLivre}
        showSendToProblema={currentStep === 1}
        onSendToProblema={(texto) => {
          const base = (problema || '').trim()
          const next = base ? `${base} ${texto.trim()}` : texto.trim()
          setProblema(next)
          setDitadoLivre('')
        }}
      />

      <UpgradeCreditsModal
        open={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
      />
    </div>
  )
}
