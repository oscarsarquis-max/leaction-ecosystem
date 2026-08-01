import { useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { CrmEvents, trackEvent } from '../lib/tracking'
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

function parseDisciplinaId(raw) {
  if (raw == null || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

/**
 * Fluxo de investigação do problema → plano do método inove4us (página própria).
 */
export default function DesafioPage() {
  const { user, logout, applyCredits, refresh } = useAuth()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  const disciplinaInicial = useMemo(() => {
    return (
      parseDisciplinaId(location.state?.disciplina_id) ||
      parseDisciplinaId(searchParams.get('disciplina_id'))
    )
  }, [location.state, searchParams])

  const [currentStep, setCurrentStep] = useState(1)
  const [problema, setProblema] = useState('')
  const [contexto, setContexto] = useState('')
  const [disciplinaId, setDisciplinaId] = useState(disciplinaInicial)
  const [trechoRelato, setTrechoRelato] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadingIa, setLoadingIa] = useState(false)

  const [causas, setCausas] = useState([])
  const [caminhos, setCaminhos] = useState([])
  const [resumoAnalise, setResumoAnalise] = useState('')
  const [referencial, setReferencial] = useState(null)
  const [fallback, setFallback] = useState(false)
  const [selectedCaminho, setSelectedCaminho] = useState(null)
  const [hipotese, setHipotese] = useState('')
  const [plano, setPlano] = useState(null)
  const [planoSession, setPlanoSession] = useState(null)
  const [ditadoLivre, setDitadoLivre] = useState('')
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [upgradeExhausted, setUpgradeExhausted] = useState(false)

  async function handleEstruturar(opts = {}) {
    const complemento = typeof opts.complementacao === 'string' ? opts.complementacao.trim() : ''
    const problemaBase = (opts.problemaOverride || problema || '').trim()
    const problemaEnvio = complemento
      ? `${problemaBase}\n\nComplemento do professor: ${complemento}`
      : problemaBase

    setError('')
    setBusy(true)
    setLoadingIa(true)
    setCurrentStep(2)
    setSelectedCaminho(null)
    setHipotese('')
    setPlano(null)
    setPlanoSession(null)
    if (complemento) {
      setProblema(problemaEnvio)
    }
    try {
      const data = await api.estruturarWizard({
        problema: problemaEnvio,
        contexto: contexto.trim(),
        id_clie: user?.id_clie,
        ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
        ...(complemento ? { complementacao: complemento } : {}),
      })
      setCausas(data.causas_raiz || [])
      setCaminhos(data.caminhos || [])
      setResumoAnalise(data.resumo_analise || '')
      setReferencial(data.referencial || null)
      setFallback(Boolean(data.fallback))
      setTrechoRelato(data.trecho_relato_usado || '')
      if (data.problema) {
        setProblema(data.problema)
      }
      void trackEvent(
        data.fallback
          ? CrmEvents.DESAFIO_ESTRUTURAR_FALLBACK
          : CrmEvents.DESAFIO_ESTRUTURAR,
        { url: '/desafio', idUsuario: user?.id_clie ?? null },
      )
      if (data.creditos_ia != null) {
        applyCredits(data.creditos_ia)
      } else {
        void refresh()
      }
    } catch (err) {
      if (!complemento) {
        setCurrentStep(1)
      }
      void trackEvent(CrmEvents.DESAFIO_ESTRUTURAR_ERRO, {
        url: '/desafio',
        idUsuario: user?.id_clie ?? null,
      })
      const code = err?.code || err?.data?.code
      if (err?.status === 403 && code === 'INSUFFICIENT_CREDITS') {
        setError('')
        applyCredits(0)
        void refresh()
        setUpgradeExhausted(true)
        setShowUpgradeModal(true)
        return
      }
      setError(err.message || 'Não foi possível estruturar o problema.')
    } finally {
      setBusy(false)
      setLoadingIa(false)
    }
  }

  function handleComplementar(texto) {
    return handleEstruturar({ complementacao: texto })
  }

  function handleSelectCaminho(caminho) {
    setSelectedCaminho(caminho)
    setHipotese(caminho?.hipotese_teste || '')
    void trackEvent(CrmEvents.CAMINHO_SELECIONAR, {
      url: `/desafio?caminho=${encodeURIComponent(caminho?.id || '')}`,
      idUsuario: user?.id_clie ?? null,
    })
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
      void trackEvent(CrmEvents.PLANO_GERAR, {
        url: '/desafio?etapa=plano',
        idUsuario: user?.id_clie ?? null,
      })
    } catch (err) {
      setHipotese(selectedCaminho.hipotese_teste)
      setPlano(selectedCaminho.plano_eduscrum)
      setPlanoSession(sessionKey)
      setCurrentStep(4)
      // Plano local ainda abre — conta como elaboração (mesmo com falha do endpoint).
      void trackEvent(CrmEvents.PLANO_GERAR, {
        url: '/desafio?etapa=plano&local=1',
        idUsuario: user?.id_clie ?? null,
      })
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
            <button
              type="button"
              onClick={() => {
                setUpgradeExhausted(false)
                setShowUpgradeModal(true)
              }}
              className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-bordo hover:bg-brand-100"
              title="Ver planos e desafios disponíveis"
            >
              {Number(user.creditos_ia)} desafio
              {Number(user.creditos_ia) === 1 ? '' : 's'}
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setUpgradeExhausted(false)
              setShowUpgradeModal(true)
            }}
            className="btn-primary !px-3 !py-1.5 text-xs"
          >
            Ver planos
          </button>
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
            disciplinaId={disciplinaId}
            onProblemaChange={setProblema}
            onContextoChange={setContexto}
            onDisciplinaChange={setDisciplinaId}
            onSubmit={handleEstruturar}
            busy={busy}
            error={error}
          />
        )}

        {currentStep === 2 && (
          <StepEstruturacao
            loading={loadingIa}
            causas={causas}
            resumoAnalise={resumoAnalise}
            referencial={referencial}
            fallback={fallback}
            onNext={() => setCurrentStep(3)}
            onComplementar={handleComplementar}
            complementBusy={busy}
          />
        )}

        {currentStep === 3 && (
          <StepHipoteses
            caminhos={caminhos}
            selectedId={selectedCaminho?.id}
            onSelect={handleSelectCaminho}
            hipotese={hipotese}
            trechoRelato={
              selectedCaminho?.trecho_relato_usado || trechoRelato
            }
            onGerarPlano={handleGerarPlano}
            busy={busy}
          />
        )}

        {currentStep === 4 && plano && (
          <StepEduScrum
            plano={plano}
            hipotese={hipotese}
            problema={problema}
            causas={causas}
            user={user}
            planoSession={planoSession}
            disciplinaId={disciplinaId}
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
        exhausted={upgradeExhausted}
        onClose={() => {
          setShowUpgradeModal(false)
          setUpgradeExhausted(false)
        }}
      />
    </div>
  )
}
