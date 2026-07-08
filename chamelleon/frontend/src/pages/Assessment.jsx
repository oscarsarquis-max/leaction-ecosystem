import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ROLE_SYSADMIN } from '../config/rbac';
import {
  getAssessmentDraft,
  getAssessmentQuestions,
  resetAssessmentDraft,
  saveAssessmentDraft,
  submitAssessment,
  updatePresentAssessment,
} from '../services/api';
import { getSession } from '../services/session';

function resolveOptionWeight(option) {
  return option?.weight ?? option?.value;
}

function resolveOptionLabel(option) {
  return (option?.label_rubr || option?.text || option?.label || '').trim();
}

function resolveOptionDescription(option) {
  return (option?.desc_rubr || option?.description || option?.desc || '').trim();
}

function resolveDisplayOrder(option, optionIndex) {
  return option?.display_order ?? optionIndex + 1;
}

function usesRubricLayout(item) {
  const options = item?.options || [];
  if (!options.length) return false;
  // Padrão PanelDX: 6 rubricas com label curto (+ descrição no hover).
  if (options.length >= 6) {
    return options.every((option) => Boolean(resolveOptionLabel(option)));
  }
  return options.every((option) => Boolean(resolveOptionDescription(option)));
}

function isPresentItem(item) {
  const prefu = String(item?.prefu_ques || '').toUpperCase();
  if (prefu === 'F') return false;
  if (prefu === 'P') return true;
  return !String(item?.axis || '').includes('(Futuro)');
}

function buildAnswersPayload(answers, itemsById, { presentOnly = false } = {}) {
  return Object.entries(answers)
    .filter(([assessmentItemId]) => {
      if (!presentOnly) return true;
      return isPresentItem(itemsById[assessmentItemId]);
    })
    .map(([assessmentItemId, optionIndex]) => {
    const item = itemsById[assessmentItemId];
    const option = item?.options?.[optionIndex];
    return {
      assessment_item_id: assessmentItemId,
      selected_value: resolveOptionWeight(option),
      option_index: optionIndex,
    };
  });
}

function restoreAnswersFromDraft(draftAnswers, itemsById) {
  const restored = {};
  for (const entry of draftAnswers || []) {
    const itemId = entry.assessment_item_id;
    const item = itemsById[itemId];
    if (!item?.options?.length) continue;

    if (
      typeof entry.option_index === 'number' &&
      entry.option_index >= 0 &&
      entry.option_index < item.options.length
    ) {
      restored[itemId] = entry.option_index;
      continue;
    }

    const matchIndex = item.options.findIndex(
      (opt) => resolveOptionWeight(opt) === entry.selected_value,
    );
    if (matchIndex >= 0) {
      restored[itemId] = matchIndex;
    }
  }
  return restored;
}

export default function Assessment() {
  const navigate = useNavigate();
  const location = useLocation();
  const { systemRole, frameworkId: sessionFrameworkId, loading: authLoading, refreshProfile } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [draftSavedAt, setDraftSavedAt] = useState(null);
  const [error, setError] = useState('');
  const [frameworkUnavailable, setFrameworkUnavailable] = useState(false);
  const [frameworkId, setFrameworkId] = useState('');
  const [dimensions, setDimensions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [isCompleted, setIsCompleted] = useState(false);
  const [submissionId, setSubmissionId] = useState(null);
  const [completedAt, setCompletedAt] = useState(null);
  const saveTimerRef = useRef(null);
  const answersRef = useRef(answers);
  const itemsByIdRef = useRef({});
  const retriedFrameworkRef = useRef(false);

  const itemsById = useMemo(() => {
    const map = {};
    for (const dimension of dimensions) {
      for (const item of dimension.items || []) {
        map[item.id] = item;
      }
    }
    return map;
  }, [dimensions]);

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  useEffect(() => {
    itemsByIdRef.current = itemsById;
  }, [itemsById]);

  useEffect(() => {
    if (!authLoading && !sessionFrameworkId && !retriedFrameworkRef.current) {
      retriedFrameworkRef.current = true;
      refreshProfile();
    }
  }, [authLoading, sessionFrameworkId, refreshProfile]);

  useEffect(() => {
    if (authLoading) return undefined;

    if (!sessionFrameworkId) {
      setFrameworkUnavailable(true);
      setFrameworkId('');
      setDimensions([]);
      setLoading(false);
      return undefined;
    }

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      setFrameworkUnavailable(false);
      try {
        if (location.state?.resetDraft) {
          await resetAssessmentDraft();
        }

        const data = await getAssessmentQuestions();
        if (cancelled) return;

        const loadedDimensions = data.dimensions || [];
        setFrameworkId(data.framework_id || sessionFrameworkId);
        setDimensions(loadedDimensions);

        const map = {};
        for (const dimension of loadedDimensions) {
          for (const item of dimension.items || []) {
            map[item.id] = item;
          }
        }

        const draftData = await getAssessmentDraft();
        if (cancelled) return;

        const payload = draftData.draft;
        if (payload?.answers?.length) {
          setAnswers(restoreAnswersFromDraft(payload.answers, map));
          setIsCompleted(payload.status === 'completed');
          setSubmissionId(payload.submission_id || null);
          setCompletedAt(payload.completed_at || null);
        } else {
          setAnswers({});
          setIsCompleted(false);
          setSubmissionId(null);
          setCompletedAt(null);
        }
      } catch (err) {
        if (!cancelled) {
          if (err.code === 'framework_unavailable' || err.status === 403) {
            setFrameworkUnavailable(true);
            setError('');
          } else {
            setError(err.message || 'Não foi possível carregar o diagnóstico.');
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [location.state?.resetDraft, sessionFrameworkId, authLoading]);

  const totalQuestions = useMemo(
    () => dimensions.reduce((acc, dim) => acc + (dim.items?.length || 0), 0),
    [dimensions],
  );

  const answeredCount = useMemo(() => Object.keys(answers).length, [answers]);

  const progressPct = totalQuestions
    ? Math.round((answeredCount / totalQuestions) * 100)
    : 0;

  const persistDraft = useCallback(async () => {
    const currentAnswers = answersRef.current;
    const entries = Object.keys(currentAnswers);
    if (entries.length === 0) return;

    const itemsMap = itemsByIdRef.current;
    const respostas = isCompleted
      ? buildAnswersPayload(currentAnswers, itemsMap, { presentOnly: true })
      : buildAnswersPayload(currentAnswers, itemsMap);

    if (isCompleted && respostas.length === 0) return;

    setSavingDraft(true);
    try {
      if (isCompleted) {
        await updatePresentAssessment({ respostas });
      } else {
        await saveAssessmentDraft({ respostas });
      }
      setDraftSavedAt(new Date());
    } catch {
      // Falha silenciosa no auto-save — o utilizador pode finalizar manualmente.
    } finally {
      setSavingDraft(false);
    }
  }, [isCompleted]);

  const handleSelect = (itemId, optionIndex) => {
    const item = itemsByIdRef.current[itemId];
    if (isCompleted && item && !isPresentItem(item)) return;

    setAnswers((prev) => {
      const next = { ...prev, [itemId]: optionIndex };
      return next;
    });

    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }
    saveTimerRef.current = setTimeout(() => {
      persistDraft();
    }, 600);
  };

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const flushOnLeave = () => {
      const currentAnswers = answersRef.current;
      if (Object.keys(currentAnswers).length === 0) return;

      const session = getSession();
      if (!session?.userId || !session?.tenantId) return;

      const respostas = isCompleted
        ? buildAnswersPayload(currentAnswers, itemsByIdRef.current, { presentOnly: true })
        : buildAnswersPayload(currentAnswers, itemsByIdRef.current);
      if (respostas.length === 0) return;

      const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
      const endpoint = isCompleted ? '/assessment/update-present' : '/assessment/draft';

      fetch(`${baseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Tenant-ID': session.tenantId,
          'X-User-ID': session.userId,
        },
        body: JSON.stringify({ respostas }),
        keepalive: true,
      });
    };

    window.addEventListener('beforeunload', flushOnLeave);
    return () => window.removeEventListener('beforeunload', flushOnLeave);
  }, [isCompleted]);

  const handleSubmit = async () => {
    if (answeredCount === 0) {
      setError('Responda pelo menos uma pergunta antes de finalizar.');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      if (isCompleted) {
        const respostas = buildAnswersPayload(answers, itemsById, { presentOnly: true });
        if (!respostas.length) {
          setError('Nenhuma resposta de Realidade (Presente) para atualizar.');
          return;
        }
        const result = await updatePresentAssessment({ respostas });
        navigate('/', {
          replace: true,
          state: { assessmentResult: result },
        });
        return;
      }

      const respostas = buildAnswersPayload(answers, itemsById);
      const result = await submitAssessment({ respostas });
      navigate('/', {
        replace: true,
        state: { assessmentResult: result },
      });
    } catch (err) {
      setError(err.message || 'Erro ao enviar diagnóstico.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center text-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-chameleon/20 border-t-chameleon" />
        <p className="mt-4 text-sm text-slate-500">Carregando questionário do framework ativo...</p>
      </div>
    );
  }

  if (frameworkUnavailable) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 py-12">
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-center shadow-sm">
          <h2 className="text-xl font-bold text-amber-900">Framework indisponível</h2>
          <p className="mt-3 text-sm leading-relaxed text-amber-800">
            Nenhum framework ativo está vinculado ao seu tenant. O administrador precisa publicar
            o framework do setor no Estúdio de Criação (Builder).
          </p>
          <button
            type="button"
            onClick={() => navigate('/')}
            className="mt-6 rounded-lg bg-chameleon px-6 py-3 text-sm font-semibold text-white hover:bg-chameleon-dark"
          >
            Voltar ao painel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8 pb-44">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-chameleon">
          Diagnóstico de Maturidade
        </p>
        <h2 className="mt-1 text-2xl font-bold text-slate-800">Avaliação Dinâmica</h2>
        <p className="mt-2 text-sm text-slate-500">
          Framework ativo:{' '}
          <span className="font-medium text-chameleon-dark">{frameworkId || '—'}</span>
        </p>
        <p className="mt-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          Questionário publicado do framework — somente leitura. As questões são definidas
          administrativamente e compartilhadas por todos os leads.
          {systemRole === ROLE_SYSADMIN && (
            <> Para editar o catálogo, use o menu <strong>Questões</strong> ou o Builder.</>
          )}
        </p>
        {isCompleted && (
          <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
            <p className="font-semibold">Diagnóstico concluído — respostas preservadas</p>
            <p className="mt-1 text-emerald-800">
              Você pode revisar todo o questionário a qualquer momento. Atualize apenas as respostas
              de <strong>Realidade (Presente)</strong> conforme o projeto evolui; Ambição (Futuro)
              permanece como referência original.
              {completedAt && (
                <span className="mt-1 block text-xs text-emerald-700">
                  Concluído em {new Date(completedAt).toLocaleString('pt-BR')}
                </span>
              )}
            </p>
            {submissionId && (
              <Link
                to={`/relatorio/${submissionId}`}
                className="mt-2 inline-flex text-sm font-semibold text-chameleon-dark underline"
              >
                Ver relatório de diagnóstico
              </Link>
            )}
          </div>
        )}
      </section>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {dimensions.map((dimension) => (
        <section
          key={dimension.name}
          className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"
        >
          <div className="border-b border-slate-100 bg-chameleon/5 px-6 py-4">
            <h3 className="text-lg font-semibold text-chameleon-dark">{dimension.name}</h3>
            <p className="text-xs text-slate-500">
              {dimension.items?.length || 0} pergunta(s) nesta dimensão
            </p>
          </div>

          <div className="divide-y divide-slate-100 px-6">
            {(dimension.items || []).map((item, index) => (
              <article key={item.id} className="py-6">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                  Pergunta {index + 1}
                </p>
                <h4 className="mt-1 text-base font-medium text-slate-800">{item.question_text}</h4>
                <p className="mt-1 text-xs text-slate-400">{item.axis}</p>

                <div
                  className={
                    usesRubricLayout(item)
                      ? 'mt-4 grid grid-cols-1 gap-1 sm:grid-cols-3 sm:gap-x-4'
                      : 'mt-4 grid gap-2 sm:grid-cols-2'
                  }
                >
                  {(item.options || []).map((option, optionIndex) => {
                    const rubricMode = usesRubricLayout(item);
                    const label = resolveOptionLabel(option);
                    const description = resolveOptionDescription(option);
                    const selected = answers[item.id] === optionIndex;
                    const readOnlyFuture = isCompleted && !isPresentItem(item);
                    return (
                      <label
                        key={`${item.id}-${optionIndex}`}
                        title={description || label}
                        className={[
                          'group relative flex items-start gap-2 transition',
                          readOnlyFuture ? 'cursor-default opacity-80' : 'cursor-pointer',
                          rubricMode
                            ? 'rounded-md px-1 py-1.5 hover:bg-slate-50'
                            : [
                                'rounded-lg border p-3 text-sm',
                                selected
                                  ? 'border-chameleon bg-chameleon/10 ring-2 ring-chameleon/30'
                                  : 'border-slate-200 hover:border-chameleon/40 hover:bg-slate-50',
                              ].join(' '),
                          rubricMode && selected ? 'bg-chameleon/10 ring-1 ring-chameleon/30 rounded-md' : '',
                        ].join(' ')}
                      >
                        <input
                          type="radio"
                          name={`question-${item.id}`}
                          value={optionIndex}
                          checked={selected}
                          disabled={readOnlyFuture}
                          onChange={() => handleSelect(item.id, optionIndex)}
                          className="mt-0.5 shrink-0 accent-chameleon"
                        />
                        <span className="min-w-0 flex-1 text-sm leading-snug text-slate-700">
                          <span className="block font-medium">{label}</span>
                          {rubricMode && description && description !== label && (
                            <span className="mt-0.5 block text-xs leading-relaxed text-slate-500">
                              {description}
                            </span>
                          )}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}

      <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-slate-200 bg-white/95 backdrop-blur lg:left-64">
        <div className="mx-auto max-w-4xl space-y-3 px-4 py-4 sm:px-8">
          <div>
            <div className="mb-2 flex justify-between text-xs font-medium text-slate-600">
              <span>
                Progresso: {answeredCount} / {totalQuestions}
                {isCompleted && (
                  <span className="ml-2 rounded bg-emerald-100 px-2 py-0.5 text-emerald-800">
                    Concluído
                  </span>
                )}
                {savingDraft && <span className="ml-2 text-chameleon">· a gravar...</span>}
                {!savingDraft && draftSavedAt && (
                  <span className="ml-2 text-slate-400">
                    · gravado às{' '}
                    {draftSavedAt.toLocaleTimeString('pt-BR', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                )}
              </span>
              <span>{progressPct}%</span>
            </div>
            <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-gradient-to-r from-chameleon-light to-chameleon transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">
              {isCompleted
                ? 'Atualize Realidade (Presente) para refletir o progresso do projeto. O relatório compara com o diagnóstico original.'
                : answeredCount === totalQuestions
                  ? 'Todas as perguntas respondidas. Pronto para enviar.'
                  : 'As respostas são gravadas automaticamente enquanto preenche.'}
            </p>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={submitting || answeredCount === 0}
              className="shrink-0 rounded-lg bg-chameleon px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-chameleon-dark disabled:cursor-not-allowed disabled:opacity-60 touch-manipulation"
            >
              {submitting
                ? 'Salvando...'
                : isCompleted
                  ? 'Atualizar realidade e relatório'
                  : 'Finalizar Diagnóstico'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
