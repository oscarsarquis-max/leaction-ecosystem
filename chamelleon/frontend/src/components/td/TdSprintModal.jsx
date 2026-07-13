import { useEffect, useMemo, useState } from 'react';
import { TD_STAGE, formatSprintBlockLabel } from '../../constants/td';
import { evaluateTdModulador, getTdSprintSquad, listProfessionals } from '../../services/tdApi';
import { fetchOkrDashboard } from '../../services/okrApi';
import TdSprintSquadSection from './TdSprintSquadSection';

function normalizeActivities(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map((item, index) => {
    if (item && typeof item === 'object') {
      const text = String(item.text || item.nome || item.nome_ativ || item.name || item.titulo || '');
      const status = String(item.status || item.status_ativ || (item.done ? 'concluida' : 'pendente'));
      return {
        id: String(item.id || item.id_ativ || `a-${index}`),
        text,
        desc: String(item.desc || item.desc_ativ || ''),
        done: Boolean(item.done ?? (status === 'concluida' || status === 'done')),
        status,
        linked_kr_id: item.linked_kr_id ? String(item.linked_kr_id) : '',
        assignee_id: item.assignee_id ? String(item.assignee_id) : '',
        contribution_value:
          item.contribution_value != null && item.contribution_value !== ''
            ? Number(item.contribution_value)
            : 1,
      };
    }
    return {
      id: `a-${index}`,
      text: String(item || ''),
      desc: '',
      done: false,
      status: 'pendente',
      linked_kr_id: '',
      assignee_id: '',
      contribution_value: 1,
    };
  });
}

function flattenKrOptions(drivers) {
  const options = [];
  for (const driver of drivers || []) {
    for (const objective of driver.objectives || []) {
      for (const kr of objective.key_results || []) {
        options.push({
          id: kr.id,
          label: `${driver.name} · ${kr.description}`,
          driver: driver.name,
          description: kr.description,
          progress_pct: kr.progress_pct,
        });
      }
    }
  }
  return options;
}

function squadMemberOptions(squad, professionals) {
  // Responsáveis de atividade = apenas membros da Squad 1:1 desta sprint.
  if (!squad?.po_id && !squad?.sm_id && !(squad?.member_ids || []).length && !(squad?.members || []).length) {
    return [];
  }
  const byId = new Map((professionals || []).map((p) => [p.id, p]));
  const ids = new Set();
  const rows = [];
  function pushId(id, roleHint) {
    if (!id || ids.has(id)) return;
    ids.add(id);
    const fromMembers = (squad.members || []).find((m) => m.id === id);
    const p = byId.get(id) || fromMembers;
    const name = p?.name || (id === squad.po_id && squad.po?.name) || (id === squad.sm_id && squad.sm?.name) || 'Membro';
    const role = roleHint || p?.role || '';
    rows.push({ id, label: role ? `${name} (${role})` : name });
  }
  pushId(squad.po_id, 'PO');
  pushId(squad.sm_id, 'SM');
  for (const m of squad.members || []) pushId(m.id, m.role);
  for (const mid of squad.member_ids || []) pushId(mid);
  return rows;
}

function initDodChecks(dod, saved) {
  const required = Array.isArray(dod?.required) ? dod.required : [];
  const education = Array.isArray(dod?.context_education) ? dod.context_education : [];
  const savedReq = saved?.required && typeof saved.required === 'object' ? saved.required : {};
  const savedEdu =
    saved?.context_education && typeof saved.context_education === 'object'
      ? saved.context_education
      : {};
  return {
    required: Object.fromEntries(required.map((item) => [item, Boolean(savedReq[item])])),
    context_education: Object.fromEntries(
      education.map((item) => [item, Boolean(savedEdu[item])]),
    ),
  };
}

function initMetrics(scores) {
  if (!scores || typeof scores !== 'object') return {};
  const next = {};
  for (const [key, value] of Object.entries(scores)) {
    const n = Number(value);
    next[key] = Number.isFinite(n) ? n : 0;
  }
  return next;
}

const RITO_OPTIONS = [
  { value: 'Daily', label: 'Daily (Diária)' },
  { value: 'Planning', label: 'Planning (Planejamento)' },
  { value: 'Review', label: 'Review (Revisão)' },
  { value: 'Retrospectiva', label: 'Retrospectiva' },
];

const ATIV_STATUS = [
  { value: 'pendente', label: 'Pendente' },
  { value: 'em_andamento', label: 'Em andamento' },
  { value: 'concluida', label: 'Concluída' },
  { value: 'bloqueada', label: 'Bloqueada' },
];

/**
 * Painel de Execução Unificada — espelho estrutural do PanelDX (sprint-atual.ejs).
 */
export default function TdSprintModal({ sprint, onClose, onSave, saving = false, onSquadChange }) {
  // Planejamento e Execução: atividades (OKR + responsável) e evidências editáveis.
  // A Squad tem API própria e permanece editável em qualquer estágio via TdSprintSquadSection.
  const editable =
    typeof onSave === 'function' ||
    sprint?.kanban_stage === TD_STAGE.EXECUCAO ||
    sprint?.kanban_stage === TD_STAGE.PLANEJADA;
  const goals = sprint?.goals_payload || {};
  const block = useMemo(() => formatSprintBlockLabel(sprint), [sprint]);
  const dod = goals.criteria_dod || {};
  const required = Array.isArray(dod.required) ? dod.required : [];
  const education = Array.isArray(dod.context_education) ? dod.context_education : [];
  const [toast, setToast] = useState({ message: '', tone: 'error' });

  const [objetivo, setObjetivo] = useState('');
  const [execNotes, setExecNotes] = useState('');
  const [realv, setRealv] = useState(0);
  const [activities, setActivities] = useState([]);
  const [showAtivModal, setShowAtivModal] = useState(false);
  const [ativDraft, setAtivDraft] = useState({
    text: '',
    desc: '',
    status: 'pendente',
    linked_kr_id: '',
    assignee_id: '',
  });
  const [krOptions, setKrOptions] = useState([]);
  const [professionals, setProfessionals] = useState([]);
  const [squad, setSquad] = useState(sprint?.squad || null);
  const [dodChecks, setDodChecks] = useState({ required: {}, context_education: {} });
  const [metrics, setMetrics] = useState({});
  const [evidencia, setEvidencia] = useState('');
  const [evidencias, setEvidencias] = useState([]);
  const [novaEvidenciaUrl, setNovaEvidenciaUrl] = useState('');
  const [novaEvidenciaComp, setNovaEvidenciaComp] = useState('');
  const [cerimonias, setCerimonias] = useState([]);
  const [ritoTipo, setRitoTipo] = useState('Daily');
  const [ritoData, setRitoData] = useState(() => new Date().toISOString().slice(0, 10));
  const [ritoNotas, setRitoNotas] = useState('');
  const [ritoFeedback, setRitoFeedback] = useState('');
  const [ritoSaving, setRitoSaving] = useState(false);
  const [chat, setChat] = useState([]);
  const [veredito, setVeredito] = useState(null);
  const [moduladorStatus, setModuladorStatus] = useState('');
  const [modulando, setModulando] = useState(false);
  const [moduladorError, setModuladorError] = useState('');
  const [consoleMsg, setConsoleMsg] = useState(
    'Aguardando mapeamento dos vetores operacionais para disparar auditoria cruzada…',
  );

  useEffect(() => {
    if (!sprint) return;
    const g = sprint.goals_payload || {};
    setObjetivo(g.objetivo || sprint.description || g.desc_sprn || '');
    setExecNotes(g.exec_notes || '');
    setRealv(Number(g.realv_sprn || 0));
    setActivities(normalizeActivities(g.atividades_execucao || g.atividades_taticas));
    setDodChecks(initDodChecks(g.criteria_dod || {}, g.dod_checks));
    setMetrics(initMetrics(g.metrics_scores));
    setEvidencia(g.evidencia_texto || '');
    setEvidencias(Array.isArray(g.evidencias) ? g.evidencias : []);
    setSquad(sprint.squad || null);
    setCerimonias(Array.isArray(g.cerimonias) ? g.cerimonias : []);
    const history = Array.isArray(g.modulador_chat) ? g.modulador_chat : [];
    setChat(history);
    const fb =
      g.modulador_feedback && typeof g.modulador_feedback === 'object'
        ? g.modulador_feedback
        : null;
    setVeredito(fb);
    setModuladorStatus(g.modulador_status || '');
    setModuladorError('');
    setRitoFeedback('');
    setRitoSaving(false);
    if (fb?.feedback) {
      setConsoleMsg(fb.feedback);
    } else if (history.length) {
      const last = history[history.length - 1];
      setConsoleMsg(last?.content || 'Histórico do Modulador carregado.');
    } else {
      setConsoleMsg(
        'Aguardando mapeamento dos vetores operacionais para disparar auditoria cruzada…',
      );
    }
  }, [sprint]);

  useEffect(() => {
    let cancelled = false;
    async function loadLinks() {
      try {
        const [okrRes, poolRes, squadRes] = await Promise.all([
          fetchOkrDashboard().catch(() => ({ drivers: [] })),
          listProfessionals({ activeOnly: true }).catch(() => ({ professionals: [] })),
          sprint?.id
            ? getTdSprintSquad(sprint.id).catch(() => ({ squad: sprint.squad || null }))
            : Promise.resolve({ squad: sprint?.squad || null }),
        ]);
        if (cancelled) return;
        setKrOptions(flattenKrOptions(okrRes.drivers || []));
        setProfessionals(poolRes.professionals || []);
        if (squadRes.squad) setSquad(squadRes.squad);
      } catch {
        /* opções auxiliares — não bloqueia o painel */
      }
    }
    loadLinks();
    return () => {
      cancelled = true;
    };
  }, [sprint?.id]);

  const assigneeOptions = useMemo(
    () => squadMemberOptions(squad, professionals),
    [squad, professionals],
  );

  if (!sprint) return null;

  const progress = Math.min(100, Math.max(0, Number(realv) || 0));
  const metricEntries = Object.entries(metrics);
  const aprovado = moduladorStatus === 'Aprovado';

  function buildGoalsPayload() {
    return {
      objetivo,
      desc_sprn: objetivo,
      exec_notes: execNotes,
      realv_sprn: Number(realv) || 0,
      atividades_taticas: activities.map((a) => a.text).filter(Boolean),
      atividades_execucao: activities,
      dod_checks: dodChecks,
      metrics_scores: metrics,
      evidencia_texto: evidencia,
      evidencias,
      cerimonias,
      modulador_chat: chat,
      modulador_status: moduladorStatus,
      modulador_feedback: veredito,
    };
  }

  async function handleSave() {
    if (!onSave) return;
    for (const item of activities) {
      if (!item.text?.trim()) continue;
      if (!item.linked_kr_id) {
        setToast({
          message: `Atividade "${item.text}": vincule a um Key Result (OKR).`,
          tone: 'error',
        });
        return;
      }
      if (!item.assignee_id) {
        setToast({
          message: `Atividade "${item.text}": atribua a um membro da equipe.`,
          tone: 'error',
        });
        return;
      }
    }
    await onSave({ goals_payload: buildGoalsPayload() });
  }

  function updateActivity(id, patch) {
    if (!editable) return;
    setActivities((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        const next = { ...item, ...patch };
        if ('status' in patch) {
          next.done = patch.status === 'concluida';
        }
        if ('done' in patch) {
          next.status = patch.done ? 'concluida' : 'pendente';
        }
        return next;
      }),
    );
  }

  function saveAtivDraft() {
    const text = ativDraft.text.trim();
    if (!text || !editable) return;
    if (!ativDraft.linked_kr_id) {
      setToast({ message: 'Selecione o Key Result (OKR) da atividade.', tone: 'error' });
      return;
    }
    if (!ativDraft.assignee_id) {
      setToast({ message: 'Atribua a atividade a um membro da squad.', tone: 'error' });
      return;
    }
    setActivities((prev) => [
      ...prev,
      {
        id: `a-${Date.now()}`,
        text,
        desc: ativDraft.desc.trim(),
        status: ativDraft.status,
        done: ativDraft.status === 'concluida',
        linked_kr_id: ativDraft.linked_kr_id,
        assignee_id: ativDraft.assignee_id,
        contribution_value: 1,
      },
    ]);
    setAtivDraft({
      text: '',
      desc: '',
      status: 'pendente',
      linked_kr_id: '',
      assignee_id: '',
    });
    setShowAtivModal(false);
  }

  function toggleDod(group, item) {
    if (!editable) return;
    setDodChecks((prev) => ({
      ...prev,
      [group]: { ...prev[group], [item]: !prev[group]?.[item] },
    }));
  }

  function setMetric(name, value) {
    if (!editable) return;
    const n = Math.max(0, Math.min(100, Number(value) || 0));
    setMetrics((prev) => {
      const next = { ...prev, [name]: n };
      const vals = Object.values(next);
      if (vals.length) {
        setRealv(Math.round(vals.reduce((a, b) => a + Number(b), 0) / vals.length));
      }
      return next;
    });
  }

  function addEvidencia() {
    const url = novaEvidenciaUrl.trim();
    if (!url || !editable) return;
    setEvidencias((prev) => [
      ...prev,
      {
        id: `e-${Date.now()}`,
        url,
        componente: novaEvidenciaComp.trim() || 'Evidência',
        status: 'Vinculada',
      },
    ]);
    setNovaEvidenciaUrl('');
    setNovaEvidenciaComp('');
    setConsoleMsg(`Evidência vinculada: ${url}. Pronta para auditoria do Modulador.`);
  }

  function removeEvidencia(id) {
    if (!editable) return;
    setEvidencias((prev) => prev.filter((e) => e.id !== id));
  }

  async function addCerimonia(event) {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    if (!editable) {
      setRitoFeedback('Abra a sprint pela coluna Em Execução para registrar ritos.');
      return;
    }
    const notas = ritoNotas.trim();
    if (!notas) {
      setRitoFeedback('Informe as notas do rito antes de registrar.');
      return;
    }
    const entry = {
      id: `c-${Date.now()}`,
      tipo: ritoTipo,
      data: ritoData || new Date().toISOString().slice(0, 10),
      notas,
    };
    const next = [entry, ...cerimonias];
    setCerimonias(next);
    setRitoNotas('');
    setRitoFeedback('Rito adicionado à linha do tempo.');
    if (!onSave) return;
    setRitoSaving(true);
    try {
      await onSave({
        goals_payload: {
          ...buildGoalsPayload(),
          cerimonias: next,
        },
      });
      setRitoFeedback('Rito registrado e salvo.');
    } catch (err) {
      setRitoFeedback(err.message || 'Rito ficou na tela, mas falhou ao salvar.');
    } finally {
      setRitoSaving(false);
    }
  }

  async function submeterModulador() {
    if (!editable || !sprint?.id) return;
    setModulando(true);
    setModuladorError('');
    setConsoleMsg('Modulador em análise… comparando evidência com o DoD.');
    try {
      if (onSave) await onSave({ goals_payload: buildGoalsPayload() });
      const res = await evaluateTdModulador(sprint.id, evidencia);
      const verdict = res.veredito || {
        status: res.modulador_status,
        nota: res.nota,
        feedback: res.feedback,
        pontos_fortes: res.pontos_fortes || [],
        pendencias: res.pendencias || [],
      };
      setVeredito(verdict);
      setModuladorStatus(verdict.status || '');
      if (typeof verdict.nota === 'number') setRealv(verdict.nota);
      setConsoleMsg(verdict.feedback || verdict.status || 'Avaliação concluída.');
      const history =
        res.sprint?.goals_payload?.modulador_chat ||
        [
          ...chat,
          { role: 'user', content: evidencia, at: new Date().toISOString() },
          {
            role: 'modulador',
            content: verdict.feedback || verdict.status,
            veredito: verdict,
            at: new Date().toISOString(),
          },
        ];
      setChat(history);
      if (res.sprint) {
        window.dispatchEvent(new CustomEvent('td-sprint-modulador-done', { detail: res }));
      }
    } catch (err) {
      const msg = err.message || 'Falha ao submeter ao Modulador.';
      setModuladorError(msg);
      setConsoleMsg(msg);
    } finally {
      setModulando(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/55 p-2 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="td-sprint-modal-title"
      onClick={onClose}
    >
      <div
        className="flex max-h-[96vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div>
            <h2 id="td-sprint-modal-title" className="text-xl font-black text-slate-900">
              Painel de Execução Unificada
            </h2>
            <p className="mt-1 text-sm font-semibold text-chameleon-dark">
              {goals.name_sprn || sprint.title}
              {block?.pair ? ` · ${block.pair}` : ''}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            onClick={onClose}
          >
            Fechar
          </button>
        </header>

        <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[1.55fr_0.95fr]">
          {/* ——— Coluna esquerda (vetores) ——— */}
          <div className="space-y-4 overflow-y-auto p-4 sm:p-5">
            <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-[11px] font-black uppercase tracking-wide text-slate-800">
                    Definição do Entregável
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                    {goals.derv_defi || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-black uppercase tracking-wide text-slate-800">
                    Composição Metodológica Exigida
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                    {goals.derv_comp || '—'}
                  </p>
                </div>
              </div>
              {editable && (
                <label className="mt-4 block text-xs font-semibold text-slate-600">
                  Objetivo / descrição da sprint
                  <textarea
                    value={objetivo}
                    onChange={(e) => setObjetivo(e.target.value)}
                    rows={2}
                    className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  />
                </label>
              )}
            </section>

            {sprint?.id && (
              <TdSprintSquadSection
                sprintId={sprint.id}
                initialSquad={sprint.squad || squad || null}
                onSaved={(nextSquad) => {
                  setSquad(nextSquad);
                  setToast({ message: 'Squad salva com sucesso.', tone: 'success' });
                  onSquadChange?.(nextSquad);
                }}
                onError={(msg) => {
                  const burnout =
                    typeof msg === 'string' &&
                    msg.toLowerCase().includes('3 sprints em execução');
                  setToast({
                    message: burnout
                      ? 'Este profissional já está alocado em 3 Sprints em execução.'
                      : msg,
                    tone: 'error',
                  });
                }}
              />
            )}

            {/* Vetor 1 */}
            <fieldset className="rounded-xl border border-chameleon/30 p-4">
              <legend className="px-2 text-xs font-black uppercase tracking-wide text-chameleon-dark">
                Vetor 1: Comprovação Documental / Relato Verbal
              </legend>

              <div className="mt-2 grid gap-2 rounded-lg border border-chameleon/20 bg-chameleon/5 p-3 sm:grid-cols-[1.4fr_1fr_auto]">
                <label className="text-xs font-bold text-chameleon-dark">
                  Link da Evidência (Drive/SharePoint)
                  <input
                    type="url"
                    disabled={!editable}
                    value={novaEvidenciaUrl}
                    onChange={(e) => setNovaEvidenciaUrl(e.target.value)}
                    placeholder="https://…"
                    className="mt-1 w-full rounded-lg border border-chameleon/30 bg-white px-3 py-2 text-sm"
                  />
                </label>
                <label className="text-xs font-bold text-chameleon-dark">
                  Componente vinculado
                  <input
                    type="text"
                    disabled={!editable}
                    value={novaEvidenciaComp}
                    onChange={(e) => setNovaEvidenciaComp(e.target.value)}
                    placeholder="Ex.: Plano, Ata, Portal"
                    className="mt-1 w-full rounded-lg border border-chameleon/30 bg-white px-3 py-2 text-sm"
                  />
                </label>
                <button
                  type="button"
                  disabled={!editable}
                  onClick={addEvidencia}
                  className="self-end rounded-lg bg-chameleon px-3 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
                >
                  + Vincular
                </button>
              </div>

              <div className="mt-3 overflow-hidden rounded-lg border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-chameleon/10 text-xs uppercase text-chameleon-dark">
                    <tr>
                      <th className="px-3 py-2">Componente</th>
                      <th className="px-3 py-2">Link</th>
                      <th className="px-3 py-2 text-center">Status Modulador</th>
                      <th className="px-3 py-2 text-center">Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evidencias.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-3 py-4 text-center text-slate-400">
                          Nenhuma evidência vinculada.
                        </td>
                      </tr>
                    )}
                    {evidencias.map((ev) => (
                      <tr key={ev.id || ev.url} className="border-t border-slate-100">
                        <td className="px-3 py-2 font-medium text-slate-800">
                          {ev.componente || 'Evidência'}
                        </td>
                        <td className="max-w-[180px] truncate px-3 py-2">
                          <a
                            href={ev.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-chameleon-dark hover:underline"
                          >
                            {ev.url}
                          </a>
                        </td>
                        <td className="px-3 py-2 text-center text-xs text-slate-600">
                          {ev.status || 'Vinculada'}
                        </td>
                        <td className="px-3 py-2 text-center">
                          {editable && (
                            <button
                              type="button"
                              className="text-xs font-semibold text-red-600 hover:underline"
                              onClick={() => removeEvidencia(ev.id)}
                            >
                              Remover
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Submissão ao Modulador — sempre visível */}
              <div className="mt-4 overflow-hidden rounded-xl border border-chameleon/40 bg-white text-slate-900 shadow-sm">
                <div className="flex items-start gap-3 border-b border-chameleon/20 bg-gradient-to-r from-chameleon/10 to-white px-4 py-3">
                  <span className="text-chameleon" aria-hidden>
                    ◆
                  </span>
                  <div>
                    <h4 className="text-sm font-bold text-chameleon-dark">Submissão ao Modulador Consultor LeAction</h4>
                    <p className="mt-0.5 text-xs text-slate-600">
                      Descreva ou cole a evidência. O Modulador compara com os Critérios de Aceite
                      (DoD).
                    </p>
                  </div>
                </div>
                <div className="space-y-3 bg-slate-50 p-4 text-slate-900">
                  <textarea
                    value={evidencia}
                    onChange={(e) => setEvidencia(e.target.value)}
                    disabled={!editable}
                    rows={6}
                    placeholder="Cole evidências, URLs (https://…), atas e provas materiais…"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm disabled:bg-slate-100"
                  />
                  <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                    <strong>Atenção:</strong> o Modulador é rigoroso. Se o critério exige link ou
                    e-mail, cole-os acima ou a sprint será reprovada.
                  </p>
                  {editable && (
                    <button
                      type="button"
                      disabled={modulando || evidencia.trim().length < 10}
                      onClick={submeterModulador}
                      className="rounded-lg bg-chameleon px-4 py-2.5 text-sm font-bold text-white hover:bg-chameleon-dark disabled:opacity-50"
                    >
                      {modulando
                        ? 'Modulador analisando…'
                        : 'Submeter para Análise do Modulador'}
                    </button>
                  )}
                  {moduladorError && <p className="text-sm text-red-700">{moduladorError}</p>}

                  {/* Resultado sempre montado */}
                  <div
                    className={`overflow-hidden rounded-xl border ${
                      aprovado
                        ? 'border-emerald-500'
                        : veredito
                          ? 'border-amber-500'
                          : 'border-slate-200'
                    }`}
                  >
                    <div
                      className={`flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-sm font-bold text-white ${
                        aprovado ? 'bg-chameleon-dark' : veredito ? 'bg-amber-600' : 'bg-slate-500'
                      }`}
                    >
                      <span>Resultado da Avaliação</span>
                      <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs">
                        {veredito?.status || 'Aguardando submissão'}
                        {typeof veredito?.nota === 'number' ? ` · ${veredito.nota}` : ''}
                      </span>
                    </div>
                    <div className="space-y-3 bg-white p-4 text-sm">
                      <p className="whitespace-pre-wrap text-slate-800">
                        {veredito?.feedback ||
                          'O parecer do Modulador aparecerá aqui após a análise.'}
                      </p>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div>
                          <p className="text-[11px] font-bold uppercase text-emerald-700">
                            Pontos fortes
                          </p>
                          <ul className="mt-1 list-disc pl-4 text-slate-700">
                            {(veredito?.pontos_fortes || []).length === 0 && (
                              <li className="text-slate-400">—</li>
                            )}
                            {(veredito?.pontos_fortes || []).map((p) => (
                              <li key={p}>{p}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-[11px] font-bold uppercase text-amber-800">
                            Pendências
                          </p>
                          <ul className="mt-1 list-disc pl-4 text-slate-700">
                            {(veredito?.pendencias || []).length === 0 && (
                              <li className="text-slate-400">—</li>
                            )}
                            {(veredito?.pendencias || []).map((p) => (
                              <li key={p}>{p}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </fieldset>

            {/* Vetor 2 — Atividades */}
            <fieldset className="rounded-xl border border-slate-200 p-4">
              <legend className="px-2 text-xs font-black uppercase tracking-wide text-slate-800">
                Vetor 2: Atividades Táticas da Sprint
              </legend>
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-xs text-slate-500">
                  Cada atividade exige vínculo a um KR e um responsável da Squad desta sprint
                  (formada no planejamento; ajustável na execução). Concluir computa a meta do OKR.
                </p>
                {editable && (
                  <button
                    type="button"
                    onClick={() => setShowAtivModal(true)}
                    className="rounded-lg bg-chameleon px-3 py-1.5 text-xs font-semibold text-white hover:bg-chameleon-dark"
                  >
                    + Nova Atividade
                  </button>
                )}
              </div>
              <div className="max-h-80 space-y-2 overflow-y-auto">
                {activities.length === 0 && (
                  <p className="py-4 text-center text-sm text-slate-400">
                    Sem atividades. Use Nova Atividade.
                  </p>
                )}
                {activities.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0 flex-1 space-y-2">
                        {editable ? (
                          <input
                            value={item.text}
                            onChange={(e) => updateActivity(item.id, { text: e.target.value })}
                            className="w-full rounded border border-slate-200 px-2 py-1 text-sm font-semibold text-slate-900"
                          />
                        ) : (
                          <p className="text-sm font-semibold text-slate-900">{item.text}</p>
                        )}
                        {(item.desc || editable) && (
                          <textarea
                            value={item.desc || ''}
                            disabled={!editable}
                            onChange={(e) => updateActivity(item.id, { desc: e.target.value })}
                            rows={2}
                            placeholder="Detalhe operacional…"
                            className="w-full rounded border border-slate-100 px-2 py-1 text-xs text-slate-600 disabled:bg-transparent"
                          />
                        )}
                        <div className="grid gap-2 rounded-lg border border-chameleon/20 bg-chameleon/5 p-2 sm:grid-cols-2">
                          <label className="block text-[11px] font-bold text-chameleon-dark">
                            Vínculo OKR — Key Result *
                            <select
                              disabled={!editable}
                              required
                              value={item.linked_kr_id || ''}
                              onChange={(e) =>
                                updateActivity(item.id, { linked_kr_id: e.target.value })
                              }
                              className="mt-0.5 w-full rounded border border-chameleon/30 bg-white px-2 py-1.5 text-xs text-slate-900"
                            >
                              <option value="">Selecione o KR…</option>
                              {krOptions.map((kr) => (
                                <option key={kr.id} value={kr.id}>
                                  {kr.label}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="block text-[11px] font-bold text-chameleon-dark">
                            Responsável (1 membro da Squad) *
                            <select
                              disabled={!editable}
                              required
                              value={item.assignee_id || ''}
                              onChange={(e) =>
                                updateActivity(item.id, { assignee_id: e.target.value })
                              }
                              className="mt-0.5 w-full rounded border border-chameleon/30 bg-white px-2 py-1.5 text-xs text-slate-900"
                            >
                              <option value="">
                                {assigneeOptions.length
                                  ? 'Selecione exatamente 1 membro…'
                                  : 'Forme/salve a Squad desta sprint primeiro…'}
                              </option>
                              {assigneeOptions.map((m) => (
                                <option key={m.id} value={m.id}>
                                  {m.label}
                                </option>
                              ))}
                            </select>
                          </label>
                        </div>
                      </div>
                      <select
                        disabled={!editable}
                        value={item.status}
                        onChange={(e) => updateActivity(item.id, { status: e.target.value })}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        {ATIV_STATUS.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            </fieldset>

            {/* Vetor 3 — Ritos */}
            <fieldset className="rounded-xl border border-slate-200 p-4">
              <legend className="px-2 text-xs font-black uppercase tracking-wide text-slate-800">
                Vetor 3: Ritos, Cerimônias e Alinhamentos Coletivos
              </legend>
              <div className="mt-2 grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
                <div className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="text-xs font-bold text-slate-700">
                      Tipo de Rito
                      <select
                        disabled={!editable}
                        value={ritoTipo}
                        onChange={(e) => setRitoTipo(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      >
                        {RITO_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-xs font-bold text-slate-700">
                      Data
                      <input
                        type="date"
                        disabled={!editable}
                        value={ritoData}
                        onChange={(e) => setRitoData(e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                      />
                    </label>
                  </div>
                  <label className="block text-xs font-bold text-slate-700">
                    Notas e Deliberações do Rito (Input Verbal/Ata)
                    <textarea
                      disabled={!editable}
                      value={ritoNotas}
                      onChange={(e) => setRitoNotas(e.target.value)}
                      rows={4}
                      placeholder="Digite as notas do rito…"
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    />
                  </label>
                  {editable && (
                    <div className="space-y-2">
                      <button
                        type="button"
                        disabled={ritoSaving}
                        onClick={addCerimonia}
                        className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-50"
                      >
                        {ritoSaving ? 'Salvando rito…' : 'Registrar Este Rito'}
                      </button>
                      {ritoFeedback && (
                        <p
                          className={`text-xs ${
                            ritoFeedback.includes('Informe') || ritoFeedback.includes('falhou')
                              ? 'text-amber-800'
                              : 'text-chameleon-dark'
                          }`}
                        >
                          {ritoFeedback}
                        </p>
                      )}
                    </div>
                  )}
                </div>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="border-b border-slate-200 pb-2 text-[11px] font-black uppercase text-chameleon-dark">
                    Linha do Tempo
                  </p>
                  <div className="mt-2 max-h-56 space-y-2 overflow-y-auto">
                    {cerimonias.length === 0 && (
                      <p className="text-xs text-slate-400">Nenhum rito registrado.</p>
                    )}
                    {cerimonias.map((c) => (
                      <div
                        key={c.id || `${c.tipo}-${c.data}`}
                        className="rounded-md border border-slate-200 bg-white px-2 py-2 text-xs"
                      >
                        <p className="font-bold text-chameleon-dark">
                          {c.tipo} · {c.data}
                        </p>
                        <p className="mt-1 whitespace-pre-wrap text-slate-700">{c.notas}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </fieldset>

            {/* Métricas */}
            <fieldset className="rounded-xl border border-slate-200 p-4">
              <legend className="px-2 text-xs font-black uppercase tracking-wide text-slate-800">
                Métricas de Qualidade Associadas à Execução
              </legend>
              {metricEntries.length === 0 ? (
                <p className="text-sm text-slate-400">Sem métricas nesta sprint.</p>
              ) : (
                <div className="mt-2 grid gap-4 sm:grid-cols-2">
                  {metricEntries.map(([name, value]) => (
                    <label key={name} className="block text-xs font-semibold text-slate-700">
                      <span className="flex justify-between">
                        <span>{name}</span>
                        <span>{value}</span>
                      </span>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        disabled={!editable}
                        value={value}
                        onChange={(e) => setMetric(name, e.target.value)}
                        className="mt-2 w-full"
                      />
                    </label>
                  ))}
                </div>
              )}
            </fieldset>

            {editable && (
              <label className="block text-xs font-semibold text-slate-600">
                Notas de execução (esteira)
                <textarea
                  value={execNotes}
                  onChange={(e) => setExecNotes(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
            )}
          </div>

          {/* ——— Sidebar Modulador (sempre visível) ——— */}
          <aside className="flex min-h-0 flex-col gap-3 overflow-y-auto border-l border-slate-200 bg-gradient-to-b from-chameleon/5 to-white p-4 text-slate-800">
            <div className="rounded-xl border border-chameleon/25 bg-white p-4 shadow-sm">
              <p className="text-[10px] font-bold uppercase tracking-wide text-chameleon-dark">
                Progresso Qualitativo do Bloco
              </p>
              <p className="mt-1 text-3xl font-black text-chameleon-dark">{progress}%</p>
              <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-chameleon/15">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-chameleon-light to-chameleon transition-all"
                  style={{ width: `${Math.max(progress, progress > 0 ? 4 : 0)}%` }}
                />
              </div>
              <p className="mt-2 text-[11px] text-slate-500">
                Mínimo para Homologação: <strong className="text-chameleon-dark">80%</strong>
              </p>
              {editable && (
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={realv}
                  onChange={(e) => setRealv(e.target.value)}
                  className="mt-3 w-full rounded-lg border border-chameleon/30 bg-white px-2 py-1.5 text-sm text-slate-800"
                />
              )}
            </div>

            <div className="rounded-xl border border-chameleon/25 bg-white p-4 text-slate-900 shadow-sm">
              <h4 className="text-[11px] font-black uppercase tracking-wide text-chameleon-dark">
                Critérios de Aceite (DoD)
              </h4>
              <p className="mt-3 text-[10px] font-bold uppercase text-slate-500">Required</p>
              <ul className="mt-1 space-y-1.5 text-sm">
                {required.length === 0 && <li className="text-slate-400">—</li>}
                {required.map((item) => (
                  <li key={item} className="flex gap-2">
                    <input
                      type="checkbox"
                      disabled={!editable}
                      checked={Boolean(dodChecks.required?.[item])}
                      onChange={() => toggleDod('required', item)}
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[10px] font-bold uppercase text-slate-500">
                Context / Education
              </p>
              <ul className="mt-1 space-y-1.5 text-sm">
                {education.length === 0 && <li className="text-slate-400">—</li>}
                {education.map((item) => (
                  <li key={item} className="flex gap-2">
                    <input
                      type="checkbox"
                      disabled={!editable}
                      checked={Boolean(dodChecks.context_education?.[item])}
                      onChange={() => toggleDod('context_education', item)}
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Console Modulador Autônomo — SEMPRE visível */}
            <div className="flex min-h-[220px] flex-1 flex-col rounded-xl border border-chameleon/30 bg-white p-4 shadow-sm">
              <h4 className="text-[11px] font-black uppercase tracking-wide text-chameleon">
                Console Modulador Autônomo
              </h4>
              <div className="mt-2 flex-1 overflow-y-auto rounded-lg border border-chameleon/20 bg-chameleon/5 p-3 font-mono text-xs leading-relaxed text-chameleon-dark">
                <p className="whitespace-pre-wrap text-slate-800">{consoleMsg}</p>
                {chat.length > 0 && (
                  <div className="mt-4 space-y-2 border-t border-slate-700 pt-3">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-chameleon-dark">
                      Troca com o agente
                    </p>
                    {chat.map((msg, idx) => (
                      <div
                        key={`${msg.at || idx}-${msg.role}`}
                        className={`rounded px-2 py-1.5 ${
                          msg.role === 'user'
                            ? 'bg-slate-800 text-slate-200'
                            : 'bg-chameleon/15 text-chameleon-dark'
                        }`}
                      >
                        <p className="text-[9px] font-bold uppercase opacity-70">
                          {msg.role === 'user' ? 'Você' : 'Modulador'}
                        </p>
                        <p className="mt-0.5 whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {editable && (
              <button
                type="button"
                disabled={saving || modulando}
                onClick={handleSave}
                className="rounded-xl bg-chameleon px-4 py-3 text-sm font-bold text-white hover:bg-chameleon/100 disabled:opacity-50"
              >
                {saving ? 'Salvando…' : 'Salvar Evolução Estratégica'}
              </button>
            )}
          </aside>
        </div>
      </div>

      {/* Submodal Nova Atividade */}
      {showAtivModal && (
        <div
          className="absolute inset-0 z-[60] flex items-center justify-center bg-slate-900/40 p-4"
          onClick={() => setShowAtivModal(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-900">Nova Atividade Operacional</h3>
            <p className="mt-1 text-xs text-slate-500">
              Vincule ao OKR e atribua a um membro da squad antes de salvar.
            </p>
            <label className="mt-4 block text-xs font-semibold text-slate-700">
              Nome da atividade
              <input
                value={ativDraft.text}
                onChange={(e) => setAtivDraft((d) => ({ ...d, text: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-3 block text-xs font-semibold text-slate-700">
              Descrição
              <textarea
                value={ativDraft.desc}
                onChange={(e) => setAtivDraft((d) => ({ ...d, desc: e.target.value }))}
                rows={3}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="mt-3 block text-xs font-semibold text-slate-700">
              Key Result (OKR) *
              <select
                value={ativDraft.linked_kr_id}
                onChange={(e) => setAtivDraft((d) => ({ ...d, linked_kr_id: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">Selecione o KR…</option>
                {krOptions.map((kr) => (
                  <option key={kr.id} value={kr.id}>
                    {kr.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs font-semibold text-slate-700">
              Responsável (squad) *
              <select
                value={ativDraft.assignee_id}
                onChange={(e) => setAtivDraft((d) => ({ ...d, assignee_id: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                <option value="">
                  {assigneeOptions.length ? 'Selecione o membro…' : 'Monte a squad primeiro…'}
                </option>
                {assigneeOptions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="mt-3 block text-xs font-semibold text-slate-700">
              Status
              <select
                value={ativDraft.status}
                onChange={(e) => setAtivDraft((d) => ({ ...d, status: e.target.value }))}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              >
                {ATIV_STATUS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                onClick={() => setShowAtivModal(false)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="rounded-lg bg-chameleon px-3 py-2 text-sm font-semibold text-white"
                onClick={saveAtivDraft}
              >
                Salvar atividade
              </button>
            </div>
          </div>
        </div>
      )}
      <TdToast
        message={toast.message}
        tone={toast.tone}
        onClose={() => setToast({ message: '', tone: 'error' })}
      />
    </div>
  );
}

export function TdToast({ message, tone = 'dark', onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = setTimeout(() => onClose?.(), 4000);
    return () => clearTimeout(timer);
  }, [message, onClose]);

  if (!message) return null;
  const styles =
    tone === 'error'
      ? 'border-red-200 bg-red-50 text-red-900'
      : tone === 'success'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
        : 'border-slate-200 bg-slate-900 text-white';

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border px-4 py-3 text-sm shadow-lg ${styles}`}
      role="status"
    >
      <div className="flex items-start gap-3">
        <p className="flex-1">{message}</p>
        <button type="button" className="shrink-0 opacity-70 hover:opacity-100" onClick={onClose}>
          ×
        </button>
      </div>
    </div>
  );
}
