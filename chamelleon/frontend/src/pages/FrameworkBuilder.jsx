import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  buildFrameworkProposal,
  deleteFramework,
  fetchMethodologyStructure,
  getFramework,
  getFrameworkTaxonomy,
  importFrameworkQuestionsJson,
  listFrameworks,
  publishFramework,
  updateFramework,
} from '../services/frameworkApi';
import { exportFrameworkDefinitionPdf } from '../utils/frameworkPdfExport';
import FrameworkTaxonomyExplorer from '../components/FrameworkTaxonomyExplorer';

const CANONICAL_EDUCATION_ID = 'educacao-v1';
const EDUCATION_SECTOR_PATTERN = /^(educa[cç][aã]o|education|ensino|edu)$/i;

const APPROVAL_STATUS_LABELS = {
  under_review: 'Em análise',
  approved: 'Aprovado',
};

function approvalStatusLabel(status) {
  return APPROVAL_STATUS_LABELS[status] || status || '—';
}

function approvalStatusClass(status) {
  if (status === 'under_review') {
    return 'bg-amber-100 text-amber-900';
  }
  if (status === 'approved') {
    return 'bg-chameleon/10 text-chameleon-dark';
  }
  return 'bg-slate-100 text-slate-600';
}

const FRAMEWORK_EDITOR_TABS = [
  { id: 'geral', label: 'Geral' },
  { id: 'fontes', label: 'Fontes' },
  { id: 'operacional', label: '5ª Dimensão' },
  { id: 'blocos', label: 'Building Blocks' },
  { id: 'taxonomia', label: 'Taxonomia' },
  { id: 'exportar', label: 'Exportar' },
];

function isEducationSectorName(value) {
  return EDUCATION_SECTOR_PATTERN.test((value || '').trim());
}

function cloneProposal(result) {
  return {
    ...result,
    manifest: { ...result.manifest },
    universal_dimensions: [...(result.universal_dimensions || [])],
    operational_dimension: {
      ...result.operational_dimension,
      building_blocks: (result.operational_dimension?.building_blocks || []).map(
        (block) => ({
          ...block,
          assessment_questions: block.assessment_questions
            ? {
                present: block.assessment_questions.present
                  ? { ...block.assessment_questions.present }
                  : undefined,
                future: block.assessment_questions.future
                  ? { ...block.assessment_questions.future }
                  : undefined,
              }
            : undefined,
          assessment_question: block.assessment_question
            ? {
                ...block.assessment_question,
                options: (block.assessment_question.options || []).map((opt) => ({
                  ...opt,
                })),
              }
            : undefined,
        }),
      ),
    },
    maturity_levels: (result.maturity_levels || []).map((level) => ({ ...level })),
    sources: [...(result.sources || [])],
    research_snippets: [...(result.research_snippets || [])],
    methodology_structure: result.methodology_structure
      ? JSON.parse(JSON.stringify(result.methodology_structure))
      : null,
  };
}

export default function FrameworkBuilder() {
  const [frameworkName, setFrameworkName] = useState('');
  const [sector, setSector] = useState('');
  const [strategicGuidelines, setStrategicGuidelines] = useState('');
  const [operationalGemba, setOperationalGemba] = useState('');
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [proposal, setProposal] = useState(null);
  const [frameworks, setFrameworks] = useState([]);
  const [duplicateConflict, setDuplicateConflict] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [editorMode, setEditorMode] = useState(null);
  const [editingFrameworkId, setEditingFrameworkId] = useState(null);
  const [openingFrameworkId, setOpeningFrameworkId] = useState(null);
  const [taxonomy, setTaxonomy] = useState(null);
  const [loadingTaxonomy, setLoadingTaxonomy] = useState(false);
  const [frameworkTab, setFrameworkTab] = useState('geral');
  const [importingJson, setImportingJson] = useState(false);
  const importFileInputRef = useRef(null);

  const isReadOnly = editorMode === 'view';
  const isCanonicalReadOnly =
    isReadOnly || proposal?.is_read_only || proposal?.is_canonical;
  const isEditingSaved =
    editorMode === 'edit' && editingFrameworkId && !proposal?.is_canonical;
  const isUnderReview = proposal?.approval_status === 'under_review';
  const isApproved = proposal?.approval_status === 'approved';

  const editorTabs = useMemo(
    () =>
      isApproved
        ? [...FRAMEWORK_EDITOR_TABS, { id: 'importar', label: 'Importar JSON' }]
        : FRAMEWORK_EDITOR_TABS,
    [isApproved],
  );

  const refreshCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    try {
      const items = await listFrameworks();
      setFrameworks(items);
    } catch (err) {
      setError(err.message || 'Erro ao carregar catálogo de frameworks.');
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    refreshCatalog();
  }, [refreshCatalog]);

  useEffect(() => {
    if (proposal) {
      setFrameworkTab('geral');
    }
  }, [editingFrameworkId, proposal?.framework_id_preview]);

  const handleResearch = async () => {
    const trimmed = sector.trim();
    if (!trimmed) {
      setError('Informe o nome do setor.');
      return;
    }

    setError('');
    setSuccess('');
    setDuplicateConflict(null);
    setEditorMode('create');
    setEditingFrameworkId(null);
    setLoading(true);
    setProposal(null);

    try {
      if (isEducationSectorName(trimmed)) {
        const result = await getFramework(CANONICAL_EDUCATION_ID);
        setProposal(cloneProposal(result));
        setEditorMode('view');
        setEditingFrameworkId(CANONICAL_EDUCATION_ID);
        await loadTaxonomyForFramework(CANONICAL_EDUCATION_ID, result.taxonomy);
        setSuccess(
          'Framework Educação carregado do catálogo base (sem pesquisa web nem IA).',
        );
        return;
      }

      const result = await buildFrameworkProposal(trimmed, {
        strategicGuidelines,
        operationalGemba,
        frameworkName,
      });
      const cloned = cloneProposal(result);
      const trimmedName = frameworkName.trim();
      if (trimmedName) {
        cloned.manifest = { ...cloned.manifest, name: trimmedName };
      }
      setProposal(cloned);
      setEditorMode('edit');
      setEditingFrameworkId(cloned.framework_id_preview || null);
      await loadTaxonomyForFramework(cloned.framework_id_preview, cloned.taxonomy);
      await refreshCatalog();
      setSuccess(
        'Framework gerado e salvo como "Em análise". Revise, edite e aprove quando estiver pronto.',
      );
    } catch (err) {
      setError(err.message || 'Erro ao gerar proposta.');
    } finally {
      setLoading(false);
    }
  };

  const updateManifest = (field, value) => {
    setProposal((prev) => ({
      ...prev,
      manifest: { ...prev.manifest, [field]: value },
    }));
  };

  const updateMaturityLevel = (index, field, value) => {
    setProposal((prev) => {
      const levels = [...prev.maturity_levels];
      levels[index] = { ...levels[index], [field]: value };
      return { ...prev, maturity_levels: levels };
    });
  };

  const updateOperationalDimension = (field, value) => {
    setProposal((prev) => ({
      ...prev,
      operational_dimension: { ...prev.operational_dimension, [field]: value },
    }));
  };

  const updateBuildingBlock = (index, field, value) => {
    setProposal((prev) => {
      const blocks = [...prev.operational_dimension.building_blocks];
      blocks[index] = { ...blocks[index], [field]: value };
      return {
        ...prev,
        operational_dimension: { ...prev.operational_dimension, building_blocks: blocks },
      };
    });
  };

  const updateBlockQuestion = (blockIndex, field, value) => {
    setProposal((prev) => {
      const blocks = [...prev.operational_dimension.building_blocks];
      blocks[blockIndex] = {
        ...blocks[blockIndex],
        assessment_question: {
          ...blocks[blockIndex].assessment_question,
          [field]: value,
        },
      };
      return {
        ...prev,
        operational_dimension: { ...prev.operational_dimension, building_blocks: blocks },
      };
    });
  };

  const updateBlockOption = (blockIndex, optIndex, field, value) => {
    setProposal((prev) => {
      const blocks = [...prev.operational_dimension.building_blocks];
      const options = [...(blocks[blockIndex].assessment_question?.options || [])];
      options[optIndex] = {
        ...options[optIndex],
        [field]: field === 'weight' ? Number(value) : value,
      };
      blocks[blockIndex] = {
        ...blocks[blockIndex],
        assessment_question: {
          ...blocks[blockIndex].assessment_question,
          options,
        },
      };
      return {
        ...prev,
        operational_dimension: { ...prev.operational_dimension, building_blocks: blocks },
      };
    });
  };

  const loadTaxonomyForFramework = useCallback(async (frameworkId, embeddedTaxonomy) => {
    if (!frameworkId) {
      setTaxonomy(null);
      return;
    }
    if (embeddedTaxonomy?.dimensions?.length) {
      setTaxonomy(embeddedTaxonomy);
      return;
    }
    setLoadingTaxonomy(true);
    try {
      const data = await getFrameworkTaxonomy(frameworkId);
      setTaxonomy(data);
    } catch {
      setTaxonomy(embeddedTaxonomy || null);
    } finally {
      setLoadingTaxonomy(false);
    }
  }, []);

  const handleCloseEditor = () => {
    setProposal(null);
    setEditorMode(null);
    setEditingFrameworkId(null);
    setDuplicateConflict(null);
    setSector('');
    setTaxonomy(null);
  };

  const handleOpenFramework = async (frameworkId, mode) => {
    setError('');
    setSuccess('');
    setDuplicateConflict(null);
    setOpeningFrameworkId(frameworkId);
    setLoading(true);
    setProposal(null);

    try {
      const result = await getFramework(frameworkId);
      const effectiveMode =
        frameworkId === CANONICAL_EDUCATION_ID || result.is_read_only ? 'view' : mode;
      setProposal(cloneProposal(result));
      setSector(result.sector || '');
      setEditorMode(effectiveMode);
      setEditingFrameworkId(frameworkId);
      await loadTaxonomyForFramework(frameworkId, result.taxonomy);
      window.scrollTo({ top: 320, behavior: 'smooth' });
    } catch (err) {
      setError(err.message || 'Erro ao carregar framework.');
    } finally {
      setLoading(false);
      setOpeningFrameworkId(null);
    }
  };

  const handleSaveEdits = async () => {
    if (!proposal || !editingFrameworkId) return;

    setError('');
    setSuccess('');
    setPublishing(true);

    try {
      const result = await updateFramework(editingFrameworkId, buildPublishPayload());
      setSuccess(result.message || 'Framework atualizado com sucesso.');
      await refreshCatalog();
    } catch (err) {
      setError(err.message || 'Erro ao salvar alterações.');
    } finally {
      setPublishing(false);
    }
  };

  const buildPublishPayload = () => ({
    sector: proposal.sector || sector,
    framework_id_preview: proposal.framework_id_preview,
    sources: proposal.sources,
    manifest: proposal.manifest,
    universal_dimensions: proposal.universal_dimensions,
    operational_dimension: proposal.operational_dimension,
    maturity_levels: proposal.maturity_levels,
  });

  const handleExportPdf = async () => {
    if (!proposal) return;
    setError('');
    setSuccess('');
    setExportingPdf(true);
    try {
      let methodologyStructure = proposal.methodology_structure;
      const frameworkId = editingFrameworkId || proposal.framework_id_preview;
      if (!methodologyStructure && frameworkId) {
        methodologyStructure = await fetchMethodologyStructure(null, frameworkId);
      }

      const exportPayload = {
        ...proposal,
        ...buildPublishPayload(),
        sector: proposal.sector || sector,
        research_snippets: proposal.research_snippets,
        methodology_structure: methodologyStructure,
      };

      const filename = await exportFrameworkDefinitionPdf(exportPayload, {
        sector: proposal.sector || sector,
      });
      setSuccess(`PDF gerado: ${filename}`);
    } catch (err) {
      setError(err.message || 'Erro ao gerar o PDF do framework.');
    } finally {
      setExportingPdf(false);
    }
  };

  const handleImportJsonClick = () => {
    importFileInputRef.current?.click();
  };

  const handleImportJsonFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    const frameworkId = editingFrameworkId || proposal?.framework_id_preview;
    if (!frameworkId) {
      setError('Abra um framework salvo antes de importar questões.');
      return;
    }

    setImportingJson(true);
    setError('');
    setSuccess('');
    try {
      const result = await importFrameworkQuestionsJson(frameworkId, file);
      setSuccess(
        result.message ||
          `${result.imported_count ?? 0} questão(ões) importada(s) com sucesso.`,
      );
      const refreshed = await getFramework(frameworkId);
      setProposal(cloneProposal(refreshed));
      await refreshCatalog();
    } catch (err) {
      setError(err.message || 'Erro ao importar questões via JSON.');
    } finally {
      setImportingJson(false);
    }
  };

  const handlePublish = async ({ replace = false } = {}) => {
    if (!proposal) return;

    setError('');
    setSuccess('');
    if (!replace) {
      setDuplicateConflict(null);
    }
    setPublishing(true);

    try {
      const result = await publishFramework(buildPublishPayload(), { replace });

      if (result.status === 'exists') {
        setDuplicateConflict({
          frameworkId: result.framework_id,
          name: result.name,
          message: result.message,
        });
      } else {
        setDuplicateConflict(null);
        const approved = result.status === 'approved' || result.status === 'replaced';
        setSuccess(
          result.message ||
            (approved
              ? `Framework "${result.name || result.framework_id}" aprovado com sucesso.`
              : `Framework "${result.name || result.framework_id}" atualizado.`),
        );
        if (approved) {
          setProposal(null);
          setSector('');
          setEditorMode(null);
          setEditingFrameworkId(null);
        } else if (result.approval_status) {
          setProposal((prev) =>
            prev ? { ...prev, approval_status: result.approval_status } : prev,
          );
        }
      }

      await refreshCatalog();
    } catch (err) {
      setError(err.message || 'Erro ao publicar framework.');
    } finally {
      setPublishing(false);
    }
  };

  const handleDeleteFromCatalog = async (frameworkId, frameworkName) => {
    const confirmed = window.confirm(
      `Remover "${frameworkName}" (${frameworkId}) do catálogo? Esta ação não pode ser desfeita.`,
    );
    if (!confirmed) return;

    setError('');
    setSuccess('');
    setDeletingId(frameworkId);

    try {
      const result = await deleteFramework(frameworkId);
      setSuccess(result.message || 'Framework removido do catálogo.');
      if (duplicateConflict?.frameworkId === frameworkId) {
        setDuplicateConflict(null);
      }
      if (editingFrameworkId === frameworkId) {
        handleCloseEditor();
      }
      await refreshCatalog();
    } catch (err) {
      setError(err.message || 'Erro ao remover framework.');
    } finally {
      setDeletingId(null);
    }
  };

  const sourceLinks =
    proposal?.sources?.length > 0
      ? proposal.sources
      : (proposal?.research_snippets || []).map((s) => s.url).filter(Boolean);

  return (
    <div className={proposal ? 'pb-28' : ''}>
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-wider text-chameleon">
          Estúdio de Criação
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-800">Framework Builder</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Configure o setor e as diretrizes de arquitetura. A IA gera a 5ª Dimensão e salva o
          framework automaticamente como <strong>Em análise</strong> para revisão e aprovação.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            Seção A — Identificação do Setor
          </h2>

          <div className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="framework-name"
                className="mb-1.5 block text-sm font-medium text-slate-700"
              >
                Nome do Framework
              </label>
              <input
                id="framework-name"
                type="text"
                value={frameworkName}
                onChange={(e) => setFrameworkName(e.target.value)}
                placeholder="Ex: Chamelleon — Construção Civil"
                disabled={loading}
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none ring-chameleon/30 transition focus:border-chameleon focus:ring-2 disabled:bg-slate-50"
              />
            </div>

            <div>
              <label htmlFor="sector" className="mb-1.5 block text-sm font-medium text-slate-700">
                Setor / Indústria
              </label>
              <input
                id="sector"
                type="text"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !loading && handleResearch()}
                placeholder="Ex: Saúde, Varejo, Construção Civil"
                disabled={loading}
                className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none ring-chameleon/30 transition focus:border-chameleon focus:ring-2 disabled:bg-slate-50"
              />
              <p className="mt-1.5 text-xs text-slate-400">
                O framework <strong>Educação</strong> já existe no catálogo base.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-100 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            Seção B — Diretrizes de Arquitetura
          </h2>

          <div className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="strategic-guidelines"
                className="mb-1.5 block text-sm font-medium text-slate-700"
              >
                Desafios Estratégicos (Quinta Dimensão)
              </label>
              <textarea
                id="strategic-guidelines"
                value={strategicGuidelines}
                onChange={(e) => setStrategicGuidelines(e.target.value)}
                placeholder="Ex: Redução de custos, integração de sistemas..."
                disabled={loading}
                rows={4}
                className="w-full resize-y rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none ring-chameleon/30 transition focus:border-chameleon focus:ring-2 disabled:bg-slate-50"
              />
            </div>

            <div>
              <label
                htmlFor="operational-gemba"
                className="mb-1.5 block text-sm font-medium text-slate-700"
              >
                Foco Operacional (Kaizen no Gemba)
              </label>
              <textarea
                id="operational-gemba"
                value={operationalGemba}
                onChange={(e) => setOperationalGemba(e.target.value)}
                placeholder="Ex: Diário de Obra, Apontamento de Horas no chão de fábrica. Especifique o módulo prático necessário."
                disabled={loading}
                rows={4}
                className="w-full resize-y rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none ring-chameleon/30 transition focus:border-chameleon focus:ring-2 disabled:bg-slate-50"
              />
            </div>

            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={handleResearch}
                disabled={loading || !sector.trim()}
                className="rounded-lg bg-chameleon px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-chameleon-dark disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? 'Gerando...' : 'Gerar Framework'}
              </button>
            </div>
          </div>
        </section>
      </div>

      {error && (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {success && (
        <p className="mt-4 rounded-lg border border-chameleon/30 bg-chameleon/5 px-4 py-3 text-sm text-chameleon-dark">
          {success}
        </p>
      )}

      <details className="mt-8 rounded-xl border border-slate-100 bg-white shadow-sm">
        <summary className="cursor-pointer list-none p-6 marker:content-none [&::-webkit-details-marker]:hidden">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-chameleon">
                Catálogo
              </p>
              <h2 className="mt-1 text-lg font-bold text-slate-800">
                Frameworks publicados ({frameworks.length})
              </h2>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                refreshCatalog();
              }}
              disabled={loadingCatalog}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-50"
            >
              Atualizar
            </button>
          </div>
        </summary>

        <div className="border-t border-slate-100 px-6 pb-6">
          {loadingCatalog ? (
            <p className="mt-4 text-sm text-slate-500">Carregando catálogo...</p>
          ) : frameworks.length === 0 ? (
            <p className="mt-4 rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
              Nenhum framework publicado ainda. Gere uma proposta, revise e clique em
              &quot;Aprovar e Publicar&quot;.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2 font-semibold">Framework</th>
                    <th className="px-3 py-2 font-semibold">Setor</th>
                    <th className="px-3 py-2 font-semibold">5ª Dimensão</th>
                    <th className="px-3 py-2 font-semibold">Itens</th>
                    <th className="px-3 py-2 font-semibold">Status</th>
                    <th className="px-3 py-2 font-semibold text-right">Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {frameworks.map((fw) => (
                    <tr key={fw.id} className="border-b border-slate-100 hover:bg-slate-50/80">
                      <td className="px-3 py-3">
                        <p className="font-medium text-slate-800">{fw.name}</p>
                        <p className="text-xs text-slate-400">{fw.id}</p>
                        {fw.is_canonical && (
                          <span className="mt-1 inline-flex rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-800">
                            Framework base
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-slate-600">{fw.sector || fw.industry}</td>
                      <td className="px-3 py-3 text-slate-600">
                        {fw.operational_dimension || '—'}
                      </td>
                      <td className="px-3 py-3 text-slate-600">
                        {fw.assessment_items_count ?? 0}
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${approvalStatusClass(fw.approval_status)}`}
                        >
                          {approvalStatusLabel(fw.approval_status)}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => handleOpenFramework(fw.id, 'view')}
                            disabled={openingFrameworkId === fw.id}
                            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
                          >
                            {openingFrameworkId === fw.id ? 'Abrindo...' : 'Ver'}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleOpenFramework(fw.id, 'edit')}
                            disabled={openingFrameworkId === fw.id || fw.is_canonical}
                            className="rounded-lg border border-chameleon/30 bg-chameleon/5 px-3 py-1.5 text-xs font-medium text-chameleon-dark transition hover:bg-chameleon/10 disabled:opacity-50"
                          >
                            Editar
                          </button>
                          {!fw.is_canonical && (
                            <button
                              type="button"
                              onClick={() => handleDeleteFromCatalog(fw.id, fw.name)}
                              disabled={deletingId === fw.id}
                              className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50"
                            >
                              {deletingId === fw.id ? 'Removendo...' : 'Remover'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </details>

      {loading && (
        <section className="mt-6 rounded-xl border border-chameleon/20 bg-white p-10 shadow-sm">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="relative h-16 w-16">
              <div className="absolute inset-0 animate-ping rounded-full bg-chameleon/20" />
              <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-chameleon/10">
                <svg
                  className="h-8 w-8 animate-spin text-chameleon"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
              </div>
            </div>
            <h3 className="mt-6 text-lg font-semibold text-slate-800">
              IA pesquisando na web...
            </h3>
            <p className="mt-2 max-w-md text-sm text-slate-500">
              Coletando referências sobre maturidade digital e boas práticas para{' '}
              <span className="font-medium text-chameleon-dark">{sector}</span>. Em seguida,
              o Claude estruturará o framework proposto.
            </p>
          </div>
        </section>
      )}

      {proposal && !loading && (
        <div className="mt-6">
          {(editorMode === 'view' || editorMode === 'edit') && (
            <section className="mb-4 rounded-xl border border-chameleon/30 bg-chameleon/5 p-4 shadow-sm">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-chameleon-dark">
                    {editorMode === 'view' ? 'Visualização' : 'Edição'} — framework salvo
                  </p>
                  <p className="mt-1 text-sm font-medium text-slate-800">
                    {proposal.manifest?.name || editingFrameworkId}
                    <span className="ml-2 font-mono text-xs text-slate-500">
                      ({editingFrameworkId})
                    </span>
                    {isUnderReview && (
                      <span
                        className={`ml-2 inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${approvalStatusClass('under_review')}`}
                      >
                        Em análise
                      </span>
                    )}
                  </p>
                  {proposal.universal_assessment_count != null && (
                    <p className="mt-1 text-xs text-slate-500">
                      {proposal.universal_assessment_count} itens universais +{' '}
                      {proposal.sector_assessment_count} itens setoriais no banco
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {editorMode === 'view' && (
                    <button
                      type="button"
                      onClick={() => setEditorMode('edit')}
                      className="rounded-lg bg-chameleon px-4 py-2 text-sm font-semibold text-white hover:bg-chameleon-dark"
                    >
                      Habilitar edição
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleCloseEditor}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            </section>
          )}

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <nav
              className="flex gap-1 overflow-x-auto border-b border-slate-200 bg-slate-50/80 px-2 py-2"
              aria-label="Seções do framework"
            >
              {editorTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setFrameworkTab(tab.id)}
                  className={[
                    'shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                    frameworkTab === tab.id
                      ? 'bg-white text-chameleon-dark shadow-sm ring-1 ring-slate-200'
                      : 'text-slate-600 hover:bg-white/70 hover:text-chameleon-dark',
                  ].join(' ')}
                >
                  {tab.label}
                </button>
              ))}
            </nav>

            <input
              ref={importFileInputRef}
              type="file"
              accept=".json,application/json"
              className="hidden"
              onChange={handleImportJsonFile}
            />

            {frameworkTab === 'importar' ? (
              <div className="p-6">
                <section className="rounded-lg border border-slate-100 bg-gradient-to-br from-white to-slate-50 p-6">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800">
                        Importar questões (JSON)
                      </h3>
                      <p className="mt-1 max-w-2xl text-sm text-slate-600">
                        Envie um arquivo <code className="text-xs">.json</code> com uma lista de
                        questões. Cada item deve conter{' '}
                        <code className="text-xs">axis</code>,{' '}
                        <code className="text-xs">question_text</code>,{' '}
                        <code className="text-xs">question_type</code>,{' '}
                        <code className="text-xs">options</code> e{' '}
                        <code className="text-xs">item_metadata</code>.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleImportJsonClick}
                      disabled={importingJson || !editingFrameworkId}
                      className="shrink-0 rounded-lg bg-chameleon px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-chameleon-dark disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {importingJson ? 'Importando...' : 'Importar Questões (JSON)'}
                    </button>
                  </div>
                  {!editingFrameworkId && (
                    <p className="mt-4 text-sm text-amber-700">
                      Salve o framework no catálogo antes de importar questões.
                    </p>
                  )}
                </section>
              </div>
            ) : (
            <fieldset
              disabled={isCanonicalReadOnly}
              className="min-w-0 border-0 p-6 m-0 disabled:opacity-95"
            >
              {frameworkTab === 'geral' && (
                <div className="space-y-6">
                  <section>
                    <h3 className="text-lg font-semibold text-slate-800">Manifesto do Framework</h3>
                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <label className="block lg:col-span-2">
                        <span className="text-sm font-medium text-slate-700">Título</span>
                        <input
                          type="text"
                          value={proposal.manifest?.name || ''}
                          onChange={(e) => updateManifest('name', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                        />
                      </label>
                      <label className="block lg:col-span-2">
                        <span className="text-sm font-medium text-slate-700">Descrição</span>
                        <textarea
                          rows={3}
                          value={proposal.manifest?.descricao || ''}
                          onChange={(e) => updateManifest('descricao', e.target.value)}
                          className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                        />
                      </label>
                    </div>
                  </section>

                  <section>
                    <h3 className="text-lg font-semibold text-slate-800">Níveis de Maturidade</h3>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      {proposal.maturity_levels.map((level, index) => (
                        <div
                          key={level.level ?? index}
                          className="rounded-lg border border-slate-100 bg-slate-50 p-4"
                        >
                          <p className="mb-3 text-xs font-semibold uppercase text-chameleon-dark">
                            Nível {level.level}
                          </p>
                          <div className="grid gap-3">
                            <label className="block">
                              <span className="text-sm font-medium text-slate-700">Nome</span>
                              <input
                                type="text"
                                value={level.name || ''}
                                onChange={(e) => updateMaturityLevel(index, 'name', e.target.value)}
                                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                              />
                            </label>
                            <label className="block">
                              <span className="text-sm font-medium text-slate-700">Descrição</span>
                              <textarea
                                rows={2}
                                value={level.description || ''}
                                onChange={(e) =>
                                  updateMaturityLevel(index, 'description', e.target.value)
                                }
                                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                              />
                            </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section>
                    <h3 className="text-lg font-semibold text-slate-800">
                      Dimensões Universais (imutáveis)
                    </h3>
                    <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                      {(proposal.universal_dimensions || []).map((dim) => (
                        <li
                          key={dim.key}
                          className="rounded-lg border border-chameleon/20 bg-chameleon/5 px-3 py-2 text-sm"
                        >
                          <span className="font-semibold text-chameleon-dark">{dim.name}</span>
                          <span className="text-slate-500"> — {dim.label}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                </div>
              )}

              {frameworkTab === 'fontes' && (
                <section>
                  <h3 className="text-lg font-semibold text-slate-800">Fontes Pesquisadas</h3>
                  <ul className="mt-4 grid gap-2 sm:grid-cols-2">
                    {sourceLinks.length === 0 ? (
                      <li className="text-sm text-slate-500">Nenhuma fonte registrada.</li>
                    ) : (
                      sourceLinks.map((url) => (
                        <li key={url}>
                          <a
                            href={url}
                            target="_blank"
                            rel="noreferrer"
                            className="block rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-chameleon-dark underline-offset-2 hover:bg-slate-100 hover:underline"
                          >
                            {url}
                          </a>
                        </li>
                      ))
                    )}
                  </ul>
                </section>
              )}

              {frameworkTab === 'operacional' && (
                <section>
                  <h3 className="text-lg font-semibold text-slate-800">
                    5ª Dimensão — Core Operacional
                  </h3>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <label className="block lg:col-span-2">
                      <span className="text-sm font-medium text-slate-700">Nome</span>
                      <input
                        type="text"
                        value={proposal.operational_dimension?.name || ''}
                        onChange={(e) => updateOperationalDimension('name', e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                      />
                    </label>
                    <label className="block">
                      <span className="text-sm font-medium text-slate-700">Sigla</span>
                      <input
                        type="text"
                        value={proposal.operational_dimension?.acronym || ''}
                        onChange={(e) => updateOperationalDimension('acronym', e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                      />
                    </label>
                    <label className="block">
                      <span className="text-sm font-medium text-slate-700">Rótulo completo</span>
                      <input
                        type="text"
                        value={proposal.operational_dimension?.full_label || ''}
                        onChange={(e) => updateOperationalDimension('full_label', e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                      />
                    </label>
                    <label className="block lg:col-span-2">
                      <span className="text-sm font-medium text-slate-700">Descrição</span>
                      <textarea
                        rows={3}
                        value={proposal.operational_dimension?.description || ''}
                        onChange={(e) => updateOperationalDimension('description', e.target.value)}
                        className="mt-1 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                      />
                    </label>
                  </div>
                </section>
              )}

              {frameworkTab === 'blocos' && (
                <section>
                  <h3 className="text-lg font-semibold text-slate-800">
                    Building Blocks — 9 Domínios Operacionais
                  </h3>
                  <div className="mt-4 grid gap-4 xl:grid-cols-2">
                    {(proposal.operational_dimension?.building_blocks || []).map(
                      (block, blockIndex) => (
                        <article
                          key={block.domain_key || blockIndex}
                          className="rounded-lg border border-slate-100 bg-slate-50 p-4"
                        >
                          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-chameleon-dark">
                            {block.domain_key} — {block.domain_name}
                          </p>
                          <div className="grid gap-3">
                            <label className="block">
                              <span className="text-sm font-medium text-slate-700">Nome do bloco</span>
                              <input
                                type="text"
                                value={block.block_name || ''}
                                onChange={(e) =>
                                  updateBuildingBlock(blockIndex, 'block_name', e.target.value)
                                }
                                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                              />
                            </label>
                            <label className="block">
                              <span className="text-sm font-medium text-slate-700">
                                Descrição do bloco
                              </span>
                              <textarea
                                rows={2}
                                value={block.block_description || ''}
                                onChange={(e) =>
                                  updateBuildingBlock(blockIndex, 'block_description', e.target.value)
                                }
                                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                              />
                            </label>
                            <label className="block">
                              <span className="text-sm font-medium text-slate-700">
                                Pergunta de diagnóstico (rascunho)
                              </span>
                              <textarea
                                rows={2}
                                value={
                                  block.assessment_questions?.present?.question_text ||
                                  block.assessment_question?.question_text ||
                                  ''
                                }
                                onChange={(e) =>
                                  updateBlockQuestion(blockIndex, 'question_text', e.target.value)
                                }
                                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-chameleon focus:ring-2 focus:ring-chameleon/20"
                              />
                            </label>
                          </div>
                        </article>
                      ),
                    )}
                  </div>
                </section>
              )}

              {frameworkTab === 'taxonomia' && (
                <section>
                  {editingFrameworkId ? (
                    <FrameworkTaxonomyExplorer taxonomy={taxonomy} loading={loadingTaxonomy} />
                  ) : (
                    <p className="text-sm text-slate-500">
                      A taxonomia metodológica estará disponível após salvar o framework.
                    </p>
                  )}
                </section>
              )}

              {frameworkTab === 'exportar' && (
                <section className="rounded-lg border border-slate-100 bg-gradient-to-br from-white to-slate-50 p-6">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-800">
                        Exportar estrutura metodológica (PDF)
                      </h3>
                      <p className="mt-1 max-w-2xl text-sm text-slate-600">
                        Exporta o conteúdo do framework: fontes, dimensões, manifesto, níveis de
                        maturidade, 5ª dimensão, building blocks e matriz PanelDX quando disponível.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleExportPdf}
                      disabled={exportingPdf || publishing}
                      className="shrink-0 rounded-lg border border-chameleon/40 bg-white px-5 py-2.5 text-sm font-semibold text-chameleon-dark shadow-sm transition hover:border-chameleon hover:bg-chameleon/5 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {exportingPdf ? 'Gerando PDF...' : 'Baixar estrutura em PDF'}
                    </button>
                  </div>
                </section>
              )}
            </fieldset>
            )}
          </div>
        </div>
      )}

      {duplicateConflict && (
        <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-900">Framework já publicado</h3>
          <p className="mt-2 text-sm text-amber-800">{duplicateConflict.message}</p>
          <p className="mt-1 text-xs text-amber-700">
            ID em conflito: <span className="font-mono">{duplicateConflict.frameworkId}</span>
            {duplicateConflict.name ? ` — ${duplicateConflict.name}` : ''}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => handlePublish({ replace: true })}
              disabled={publishing}
              className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:opacity-60"
            >
              {publishing ? 'Substituindo...' : 'Substituir versão existente'}
            </button>
            <button
              type="button"
              onClick={() =>
                handleDeleteFromCatalog(
                  duplicateConflict.frameworkId,
                  duplicateConflict.name || duplicateConflict.frameworkId,
                )
              }
              disabled={deletingId === duplicateConflict.frameworkId}
              className="rounded-lg border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-900 transition hover:bg-amber-100 disabled:opacity-60"
            >
              Remover do catálogo e publicar depois
            </button>
          </div>
        </section>
      )}

      {proposal && !loading && (
        <div className="fixed bottom-0 left-64 right-0 z-30 border-t border-slate-200 bg-white/95 px-8 py-4 backdrop-blur">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-500">
              {isEditingSaved
                ? isUnderReview
                  ? `Editando rascunho em análise (${editingFrameworkId}).`
                  : `Editando framework salvo (${editingFrameworkId}).`
                : editorMode === 'view'
                  ? 'Modo visualização — habilite a edição para alterar.'
                  : duplicateConflict
                    ? 'Escolha substituir a versão existente ou remova-a do catálogo.'
                    : 'Revise o framework e aprove quando a análise estiver concluída.'}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleExportPdf}
                disabled={exportingPdf || publishing}
                className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {exportingPdf ? 'Gerando PDF...' : 'Estrutura PDF'}
              </button>
              {isEditingSaved && (
                <>
                  <button
                    type="button"
                    onClick={handleCloseEditor}
                    className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Fechar
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveEdits}
                    disabled={publishing}
                    className="rounded-lg border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                  >
                    {publishing ? 'Salvando...' : 'Salvar alterações'}
                  </button>
                  {isUnderReview && (
                    <button
                      type="button"
                      onClick={() => handlePublish()}
                      disabled={publishing}
                      className="rounded-lg bg-chameleon px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-chameleon-dark disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {publishing ? 'Aprovando...' : 'Aprovar framework'}
                    </button>
                  )}
                </>
              )}
              {editorMode === 'view' && (
                <button
                  type="button"
                  onClick={() => setEditorMode('edit')}
                  className="rounded-lg bg-chameleon px-6 py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark"
                >
                  Editar framework
                </button>
              )}
              {editorMode === 'view' && isUnderReview && (
                <button
                  type="button"
                  onClick={() => handlePublish()}
                  disabled={publishing}
                  className="rounded-lg bg-chameleon px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-chameleon-dark disabled:opacity-60"
                >
                  {publishing ? 'Aprovando...' : 'Aprovar framework'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
