import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  createQuestion,
  deleteQuestion,
  listQuestions,
  listQuestionsAdminCatalog,
  updateQuestion,
} from '../services/api';
import { importFrameworkQuestionsJson } from '../services/frameworkApi';

const EMPTY_FORM = {
  axis: '',
  question_text: '',
  question_type: 'likert_4',
};

const EDUCATION_TAB = 'education';

function filterBySearch(items, search) {
  const term = search.trim().toLowerCase();
  if (!term) return items;
  return items.filter(
    (item) =>
      item.question_text?.toLowerCase().includes(term) ||
      item.axis?.toLowerCase().includes(term) ||
      item.dimension?.toLowerCase().includes(term),
  );
}

function QuestionsTable({ items, onEdit, onDelete }) {
  if (items.length === 0) {
    return (
      <p className="p-8 text-center text-sm text-slate-500">Nenhuma questão encontrada.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-semibold">ID</th>
            <th className="px-4 py-3 font-semibold">Texto da questão</th>
            <th className="px-4 py-3 font-semibold">Dimensão / Eixo</th>
            <th className="px-4 py-3 font-semibold">Tipo</th>
            <th className="px-4 py-3 text-center font-semibold">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-slate-50/80">
              <td className="px-4 py-3 font-mono text-xs text-slate-500">
                {String(item.id).slice(0, 8)}
              </td>
              <td className="max-w-xl px-4 py-3 text-slate-800">{item.question_text}</td>
              <td className="px-4 py-3 text-slate-600">{item.axis}</td>
              <td className="px-4 py-3 text-slate-500">{item.question_type}</td>
              <td className="px-4 py-3">
                <div className="flex items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => onEdit(item)}
                    className="rounded px-2 py-1 text-xs font-medium text-chameleon hover:bg-chameleon/10"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(item.id)}
                    className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Remover
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Questoes() {
  const { frameworkId, isAdmin } = useAuth();
  const [items, setItems] = useState([]);
  const [adminCatalog, setAdminCatalog] = useState(null);
  const [activeTab, setActiveTab] = useState(EDUCATION_TAB);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [frameworkApproved, setFrameworkApproved] = useState(false);
  const [importingJson, setImportingJson] = useState(false);
  const importFileInputRef = useRef(null);

  const loadItems = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (isAdmin) {
        const data = await listQuestionsAdminCatalog();
        setAdminCatalog(data);
        setItems([]);
      } else {
        const data = await listQuestions();
        setItems(data.items || []);
        setAdminCatalog(null);
      }
    } catch (err) {
      setError(err.message || 'Não foi possível carregar as questões.');
      setItems([]);
      setAdminCatalog(null);
    } finally {
      setLoading(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const activeFrameworkMeta = useMemo(() => {
    if (!isAdmin || !adminCatalog || activeTab === EDUCATION_TAB) return null;
    return adminCatalog.frameworks?.find((fw) => fw.id === activeTab) || null;
  }, [isAdmin, adminCatalog, activeTab]);

  const activeFrameworkId = useMemo(() => {
    if (!isAdmin) return frameworkId;
    if (activeTab === EDUCATION_TAB) {
      return adminCatalog?.education_framework_id || 'educacao-v1';
    }
    return activeTab;
  }, [isAdmin, activeTab, adminCatalog, frameworkId]);

  useEffect(() => {
    if (isAdmin) {
      if (activeTab === EDUCATION_TAB) {
        setFrameworkApproved(true);
        return;
      }
      setFrameworkApproved(activeFrameworkMeta?.approval_status === 'approved');
      return;
    }

    let cancelled = false;
    async function loadFrameworkStatus() {
      if (!frameworkId) {
        setFrameworkApproved(false);
        return;
      }
      try {
        const { listFrameworks } = await import('../services/frameworkApi');
        const frameworks = await listFrameworks();
        if (cancelled) return;
        const match = frameworks.find((fw) => fw.id === frameworkId);
        setFrameworkApproved(match?.approval_status === 'approved');
      } catch {
        if (!cancelled) setFrameworkApproved(false);
      }
    }
    loadFrameworkStatus();
    return () => {
      cancelled = true;
    };
  }, [isAdmin, frameworkId, activeTab, activeFrameworkMeta]);

  const tabItems = useMemo(() => {
    if (!isAdmin || !adminCatalog) return items;
    if (activeTab === EDUCATION_TAB) {
      return adminCatalog.education_questions || [];
    }
    return activeFrameworkMeta?.questions || [];
  }, [isAdmin, adminCatalog, activeTab, activeFrameworkMeta, items]);

  const filtered = useMemo(() => filterBySearch(tabItems, search), [tabItems, search]);

  const tabCounts = useMemo(() => {
    if (!isAdmin || !adminCatalog) return {};
    const counts = {
      [EDUCATION_TAB]: adminCatalog.education_total ?? adminCatalog.education_questions?.length ?? 0,
    };
    for (const fw of adminCatalog.frameworks || []) {
      counts[fw.id] = fw.total ?? fw.questions?.length ?? 0;
    }
    return counts;
  }, [isAdmin, adminCatalog]);

  function openCreate() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setModalOpen(true);
  }

  function openEdit(item) {
    setEditingId(item.id);
    setForm({
      axis: item.axis || '',
      question_text: item.question_text || '',
      question_type: item.question_type || 'likert_4',
    });
    setModalOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const payload = { ...form };
      if (isAdmin && activeFrameworkId && !editingId) {
        payload.framework_id = activeFrameworkId;
      }
      if (editingId) {
        await updateQuestion(editingId, payload);
      } else {
        await createQuestion(payload);
      }
      setModalOpen(false);
      await loadItems();
    } catch (err) {
      setError(err.message || 'Erro ao salvar questão.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(itemId) {
    if (!window.confirm('Remover esta questão?')) return;
    setError('');
    setSuccess('');
    try {
      await deleteQuestion(itemId);
      await loadItems();
    } catch (err) {
      setError(err.message || 'Erro ao remover questão.');
    }
  }

  function handleImportJsonClick() {
    importFileInputRef.current?.click();
  }

  async function handleImportJsonFile(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !activeFrameworkId) return;

    setImportingJson(true);
    setError('');
    setSuccess('');
    try {
      const result = await importFrameworkQuestionsJson(activeFrameworkId, file);
      setSuccess(
        result.message ||
          `${result.imported_count ?? 0} questão(ões) importada(s) com sucesso.`,
      );
      await loadItems();
    } catch (err) {
      setError(err.message || 'Erro ao importar questões via JSON.');
    } finally {
      setImportingJson(false);
    }
  }

  const activeTabLabel = useMemo(() => {
    if (!isAdmin) return null;
    if (activeTab === EDUCATION_TAB) {
      return 'Educação — 5 dimensões (base canônica)';
    }
    const fw = activeFrameworkMeta;
    if (!fw) return activeTab;
    return fw.sector ? `${fw.name} (${fw.sector})` : fw.name;
  }, [isAdmin, activeTab, activeFrameworkMeta]);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Questões (Administração)</h2>
          <p className="mt-1 text-sm text-slate-500">
            {isAdmin
              ? 'Visão global do catálogo: dimensões universais e LA no framework Educação; domínio setorial (5ª dimensão) por framework gerado.'
              : 'Catálogo do framework publicado — compartilhado por todos os leads no diagnóstico. Alterações aqui não são feitas durante o preenchimento do questionário.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {frameworkApproved && (
            <>
              <input
                ref={importFileInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={handleImportJsonFile}
              />
              <button
                type="button"
                onClick={handleImportJsonClick}
                disabled={importingJson}
                className="rounded-lg border border-chameleon/40 bg-white px-4 py-2 text-sm font-semibold text-chameleon-dark hover:bg-chameleon/5 disabled:opacity-60"
              >
                {importingJson ? 'Importando...' : 'Importar Questões (JSON)'}
              </button>
            </>
          )}
          <button
            type="button"
            onClick={openCreate}
            className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
          >
            + Nova questão
          </button>
        </div>
      </header>

      {isAdmin && adminCatalog && (
        <nav
          className="flex gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50/80 p-2"
          aria-label="Catálogos de questões"
        >
          <button
            type="button"
            onClick={() => {
              setActiveTab(EDUCATION_TAB);
              setSearch('');
            }}
            className={[
              'shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
              activeTab === EDUCATION_TAB
                ? 'bg-white text-chameleon-dark shadow-sm ring-1 ring-slate-200'
                : 'text-slate-600 hover:bg-white/70 hover:text-chameleon-dark',
            ].join(' ')}
          >
            Educação (5 dim.)
            <span className="ml-1.5 text-xs text-slate-400">({tabCounts[EDUCATION_TAB] ?? 0})</span>
          </button>
          {(adminCatalog.frameworks || []).map((fw) => (
            <button
              key={fw.id}
              type="button"
              onClick={() => {
                setActiveTab(fw.id);
                setSearch('');
              }}
              className={[
                'shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                activeTab === fw.id
                  ? 'bg-white text-chameleon-dark shadow-sm ring-1 ring-slate-200'
                  : 'text-slate-600 hover:bg-white/70 hover:text-chameleon-dark',
              ].join(' ')}
            >
              {fw.name}
              {fw.sector ? (
                <span className="ml-1 text-xs font-normal text-slate-400">({fw.sector})</span>
              ) : null}
              <span className="ml-1.5 text-xs text-slate-400">({tabCounts[fw.id] ?? 0})</span>
            </button>
          ))}
        </nav>
      )}

      {isAdmin && activeTabLabel && (
        <p className="text-sm text-slate-600">
          Exibindo: <span className="font-medium text-slate-800">{activeTabLabel}</span>
          {activeTab !== EDUCATION_TAB && (
            <span className="text-slate-400"> — apenas questões do domínio setorial (5ª dimensão)</span>
          )}
        </p>
      )}

      <div className="relative max-w-lg">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar em enunciados, dimensões ou eixos..."
          className="w-full rounded-full border border-slate-200 px-4 py-2.5 pl-10 text-sm focus:border-chameleon focus:outline-none focus:ring-2 focus:ring-chameleon/20"
        />
        <span className="pointer-events-none absolute left-3 top-2.5 text-slate-400">🔍</span>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <p className="p-8 text-center text-sm text-slate-500">Carregando questões...</p>
        ) : (
          <QuestionsTable items={filtered} onEdit={openEdit} onDelete={handleDelete} />
        )}
      </section>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-xl">
            <header className="border-b border-slate-100 px-6 py-4">
              <h3 className="text-lg font-semibold text-slate-800">
                {editingId ? 'Editar questão' : 'Nova questão'}
              </h3>
              {isAdmin && activeFrameworkId && !editingId && (
                <p className="mt-1 text-xs text-slate-500">
                  Framework: {activeTabLabel || activeFrameworkId}
                </p>
              )}
            </header>
            <form onSubmit={handleSave} className="space-y-4 px-6 py-5">
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Eixo / Dimensão</span>
                <input
                  required
                  value={form.axis}
                  onChange={(e) => setForm((f) => ({ ...f, axis: e.target.value }))}
                  placeholder="Ex.: Estratégia / Governança Digital"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <label className="block text-sm">
                <span className="font-medium text-slate-700">Enunciado</span>
                <textarea
                  required
                  rows={4}
                  value={form.question_text}
                  onChange={(e) => setForm((f) => ({ ...f, question_text: e.target.value }))}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
                >
                  {saving ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
