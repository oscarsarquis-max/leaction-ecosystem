import { useMemo, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import { CrmEvents, trackEvent } from '../lib/tracking'
import FloatingDictation from '../components/FloatingDictation'
import UpgradeCreditsModal from '../components/UpgradeCreditsModal'
import InstitutionalPlanBadge from '../components/InstitutionalPlanBadge'
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
  const [objetivo, setObjetivo] = useState('')
  const [turmaNivel, setTurmaNivel] = useState('')
  const [duracao, setDuracao] = useState('')
  const [contexto, setContexto] = useState('')
  const [metodologiaDesejadaId, setMetodologiaDesejadaId] = useState(null)
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
  const [desafioId, setDesafioId] = useState(null)
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
    setDesafioId(null)
    if (complemento) {
      setProblema(problemaEnvio)
    }
    try {
      const data = await api.estruturarWizard({
        problema: problemaEnvio,
        contexto: contexto.trim(),
        ...(objetivo.trim() ? { objetivo: objetivo.trim() } : {}),
        ...(turmaNivel.trim() ? { turma_nivel: turmaNivel.trim() } : {}),
        ...(duracao.trim() ? { duracao: duracao.trim() } : {}),
        id_clie: user?.id_clie,
        ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
        ...(metodologiaDesejadaId
          ? { metodologia_desejada_id: metodologiaDesejadaId }
          : {}),
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
        if (!user?.is_institutional) {
          setUpgradeExhausted(true)
          setShowUpgradeModal(true)
        } else {
          setError(
            'Sua licença é institucional. Se precisar de mais capacidade, fale com a coordenação da escola.',
          )
        }
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

  async function persistirDesafioComPlano({ planoObj, hipoteseTxt, sessionKey }) {
    if (!planoObj) return null
    try {
      const planData = {
        plano: planoObj,
        plano_eduscrum: planoObj,
        hipotese: hipoteseTxt || '',
        problema: problema || '',
        plano_session: sessionKey || null,
        ...(causas != null ? { causas } : {}),
      }
      const res = await api.criarDesafio({
        titulo: planoObj?.nome || planoObj?.etiqueta || undefined,
        problema: problema || undefined,
        hipotese: hipoteseTxt || undefined,
        causas: causas ?? undefined,
        plano_session: sessionKey || undefined,
        disciplina_id: disciplinaId ?? undefined,
        plan_data: planData,
        meta_json: {
          missao: planoObj?.missao || '',
          hipotese: hipoteseTxt || '',
          problema: (problema || '').slice(0, 500),
          precisa_registrar_aulas: true,
          ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
          ...(causas != null ? { causas } : {}),
          ...(sessionKey ? { plano_session: sessionKey } : {}),
        },
      })
      const id = res?.desafio_id || res?.desafio?.id || null
      if (id) setDesafioId(id)
      return id
    } catch (err) {
      console.warn('Falha ao persistir desafio após gerar cards', err)
      setError(
        err?.message ||
          'Plano gerado, mas não foi possível salvar para retomada. Registre as aulas agora ou tente de novo.',
      )
      return null
    }
  }

  async function handleGerarPlano() {
    if (!selectedCaminho) return
    setBusy(true)
    setError('')
    const sessionKey = newSessionKey()
    try {
      const data = await api.selecionarCaminho(selectedCaminho)
      const hipoteseTxt = data.hipotese_teste || selectedCaminho.hipotese_teste
      const planoObj = data.plano_eduscrum || selectedCaminho.plano_eduscrum
      setHipotese(hipoteseTxt)
      setPlano(planoObj)
      setPlanoSession(sessionKey)
      setCurrentStep(4)
      void trackEvent(CrmEvents.PLANO_GERAR, {
        url: '/desafio?etapa=plano',
        idUsuario: user?.id_clie ?? null,
      })
      // Crédito IA já foi gasto no estruturar — salva o desafio agora (gestão de execução).
      await persistirDesafioComPlano({ planoObj, hipoteseTxt, sessionKey })
    } catch (err) {
      const hipoteseTxt = selectedCaminho.hipotese_teste
      const planoObj = selectedCaminho.plano_eduscrum
      setHipotese(hipoteseTxt)
      setPlano(planoObj)
      setPlanoSession(sessionKey)
      setCurrentStep(4)
      // Plano local ainda abre — conta como elaboração (mesmo com falha do endpoint).
      void trackEvent(CrmEvents.PLANO_GERAR, {
        url: '/desafio?etapa=plano&local=1',
        idUsuario: user?.id_clie ?? null,
      })
      console.warn(err)
      await persistirDesafioComPlano({ planoObj, hipoteseTxt, sessionKey })
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
          {user?.is_institutional ? (
            <InstitutionalPlanBadge institutionalName={user?.institutional_name} />
          ) : (
            <>
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
            </>
          )}
          <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
            Sair
          </button>
        </div>
      </div>

      <main className="px-4 pb-16 pt-2 sm:px-6">
        {currentStep === 1 && (
          <StepProblema
            problema={problema}
            objetivo={objetivo}
            turmaNivel={turmaNivel}
            duracao={duracao}
            contexto={contexto}
            disciplinaId={disciplinaId}
            metodologiaDesejadaId={metodologiaDesejadaId}
            onProblemaChange={setProblema}
            onObjetivoChange={setObjetivo}
            onTurmaNivelChange={setTurmaNivel}
            onDuracaoChange={setDuracao}
            onContextoChange={setContexto}
            onDisciplinaChange={setDisciplinaId}
            onMetodologiaDesejadaChange={setMetodologiaDesejadaId}
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
          <>
            {desafioId ? (
              <div className="mx-auto mb-4 max-w-6xl rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
                <p className="font-semibold">Desafio salvo — você pode sair e retomar depois.</p>
                <p className="mt-1 text-emerald-900/90">
                  Os cards já estão prontos. O próximo passo é registrar as aulas (gestão da
                  execução). Sem nova consulta à IA.
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Link
                    to={`/desafios/${desafioId}`}
                    className="text-sm font-bold text-emerald-900 underline-offset-2 hover:underline"
                  >
                    Abrir mesa do desafio
                  </Link>
                  <Link
                    to="/mesa-do-inovador"
                    className="text-sm font-semibold text-emerald-800/90 underline-offset-2 hover:underline"
                  >
                    Ir ao início (lista de desafios)
                  </Link>
                </div>
              </div>
            ) : null}
            <StepEduScrum
              plano={plano}
              hipotese={hipotese}
              problema={problema}
              causas={causas}
              user={user}
              planoSession={planoSession}
              disciplinaId={disciplinaId}
              desafioId={desafioId}
              onVoltar={() => setCurrentStep(3)}
            />
          </>
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
        open={!user?.is_institutional && showUpgradeModal}
        exhausted={upgradeExhausted}
        onClose={() => {
          setShowUpgradeModal(false)
          setUpgradeExhausted(false)
        }}
      />
    </div>
  )
}
