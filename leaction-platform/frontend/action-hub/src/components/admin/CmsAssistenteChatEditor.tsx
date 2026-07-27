'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronRight,
  Loader2,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  fetchCmsAssistenteChatAdmin,
  saveCmsAssistenteChat,
  type CmsAssistenteChatRecord,
  type CmsPostStatus,
  type CmsSistemaDestino,
} from '@/lib/admin-api';
import {
  cloneAssistenteSeedInove4us,
  type AssistenteTree,
  type AssistenteTreeNode,
  type AssistenteTreeOption,
} from '@/lib/cms-assistente-seed-inove4us';

const DESTINOS_MVP: { value: CmsSistemaDestino; label: string }[] = [
  { value: 'inove4us', label: 'inove4us' },
];

const ACTION_WHITELIST = ['', 'open_upgrade'] as const;
const NODE_ID_RE = /^[a-z][a-z0-9_]{0,63}$/;

type EditorTab = 'visual' | 'json';

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function tryParseTree(text: string): { tree: AssistenteTree | null; error: string | null } {
  try {
    const parsed = JSON.parse(text) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      return { tree: null, error: 'JSON deve ser um objeto' };
    }
    return { tree: parsed as AssistenteTree, error: null };
  } catch (e) {
    return {
      tree: null,
      error: e instanceof Error ? e.message : 'JSON inválido',
    };
  }
}

function normalizeTree(tree: AssistenteTree): AssistenteTree {
  return {
    ...tree,
    avatar_name: String(tree.avatar_name || 'Nina'),
    avatar_tagline: String(tree.avatar_tagline || 'Guia do inovador'),
    avatar_candidates: Array.isArray(tree.avatar_candidates)
      ? tree.avatar_candidates
      : ['Nina'],
    root_id: String(tree.root_id || 'inicio'),
    nodes: tree.nodes && typeof tree.nodes === 'object' ? tree.nodes : {},
  };
}

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('pt-BR');
  } catch {
    return iso;
  }
}

function extractApiErrors(err: unknown): string[] {
  if (err && typeof err === 'object' && 'response' in err) {
    const data = (err as { response?: { data?: { error?: string; errors?: string[] } } })
      .response?.data;
    if (Array.isArray(data?.errors) && data.errors.length) {
      return data.errors.map(String);
    }
    if (data?.error) return [String(data.error)];
  }
  if (err instanceof Error && err.message) return [err.message];
  return ['Falha ao salvar'];
}

/** Validação client-side alinhada ao gateway (publish). */
function validateTreeClient(tree: AssistenteTree): string[] {
  const errors: string[] = [];
  const nodes = tree.nodes || {};
  const rootId = String(tree.root_id || '').trim();
  if (!rootId) errors.push('root_id é obrigatório');
  else if (!(rootId in nodes)) {
    errors.push(`root_id '${rootId}' não existe em nodes`);
  }
  if (!String(tree.avatar_name || '').trim()) {
    errors.push('avatar_name é obrigatório');
  }
  for (const [nid, node] of Object.entries(nodes)) {
    if (!node || typeof node !== 'object') {
      errors.push(`nodes['${nid}'] inválido`);
      continue;
    }
    if (typeof node.message !== 'string' || !node.message.trim()) {
      errors.push(`nodes['${nid}'].message deve ser string não vazia`);
    }
    if (!Array.isArray(node.options)) {
      errors.push(`nodes['${nid}'].options deve ser um array`);
      continue;
    }
    node.options.forEach((opt, idx) => {
      const prefix = `nodes['${nid}'].options[${idx}]`;
      if (!String(opt?.label || '').trim()) {
        errors.push(`${prefix}.label é obrigatório`);
      }
      if (opt.next != null && String(opt.next).trim() !== '') {
        const next = String(opt.next).trim();
        if (!(next in nodes)) {
          errors.push(`${prefix}.next '${next}' não existe em nodes`);
        }
      }
      if (opt.href != null && String(opt.href).trim() !== '') {
        const href = String(opt.href).trim();
        if (!href.startsWith('/')) {
          errors.push(`${prefix}.href deve começar com '/'`);
        }
      }
      if (opt.action != null && String(opt.action).trim() !== '') {
        const action = String(opt.action).trim();
        if (action !== 'open_upgrade') {
          errors.push(`${prefix}.action '${action}' inválida`);
        }
      }
    });
  }
  return errors;
}

function inboundRefs(tree: AssistenteTree, nodeId: string): string[] {
  const refs: string[] = [];
  for (const [nid, node] of Object.entries(tree.nodes || {})) {
    (node.options || []).forEach((opt, idx) => {
      if (String(opt.next || '').trim() === nodeId) {
        refs.push(`${nid} → options[${idx}]`);
      }
    });
  }
  return refs;
}

function snippetMessage(msg: string, max = 80): string {
  const one = String(msg || '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!one) return '(sem mensagem)';
  if (one.length <= max) return one;
  return `${one.slice(0, max - 1)}…`;
}

function childNextIds(node: AssistenteTreeNode | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const opt of node?.options || []) {
    const next = String(opt.next || '').trim();
    if (!next || seen.has(next)) continue;
    seen.add(next);
    out.push(next);
  }
  return out;
}

/** Nós alcançáveis a partir de root_id seguindo options.next. */
function computeReachable(tree: AssistenteTree): Set<string> {
  const reach = new Set<string>();
  const root = String(tree.root_id || '').trim();
  if (!root || !tree.nodes?.[root]) return reach;
  const stack = [root];
  while (stack.length) {
    const id = stack.pop()!;
    if (reach.has(id)) continue;
    reach.add(id);
    for (const next of childNextIds(tree.nodes[id])) {
      if (tree.nodes[next] && !reach.has(next)) stack.push(next);
    }
  }
  return reach;
}

type OutlineRow = {
  id: string;
  depth: number;
  pathKey: string;
  hasChildren: boolean;
  messagePreview: string;
};

function buildOutlineRows(
  tree: AssistenteTree,
  collapsed: Set<string>
): OutlineRow[] {
  const rows: OutlineRow[] = [];
  const root = String(tree.root_id || '').trim();
  if (!root || !tree.nodes?.[root]) return rows;

  function walk(id: string, depth: number, ancestry: string[]) {
    if (!tree.nodes[id]) return;
    const pathKey = [...ancestry, id].join('>');
    const children = childNextIds(tree.nodes[id]).filter((c) => !!tree.nodes[c]);
    rows.push({
      id,
      depth,
      pathKey,
      hasChildren: children.length > 0,
      messagePreview: snippetMessage(tree.nodes[id].message || '', 56),
    });
    if (collapsed.has(pathKey)) return;
    for (const child of children) {
      if (ancestry.includes(child) || child === id) {
        rows.push({
          id: child,
          depth: depth + 1,
          pathKey: `${pathKey}>${child}#ciclo`,
          hasChildren: false,
          messagePreview: `${snippetMessage(tree.nodes[child]?.message || '', 40)} (já no caminho)`,
        });
        continue;
      }
      walk(child, depth + 1, [...ancestry, id]);
    }
  }

  walk(root, 0, []);
  return rows;
}

function StatusCard({
  title,
  record,
}: {
  title: string;
  record: CmsAssistenteChatRecord | null;
}) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-stone-900">{title}</h3>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${
            record
              ? title.toLowerCase().includes('publicado')
                ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                : 'bg-amber-50 text-amber-800 ring-1 ring-amber-200'
              : 'bg-stone-100 text-stone-500 ring-1 ring-stone-200'
          }`}
        >
          {record ? 'Presente' : 'Ausente'}
        </span>
      </div>
      {record ? (
        <dl className="space-y-1 text-xs text-stone-600">
          <div className="flex justify-between gap-2">
            <dt>Atualizado</dt>
            <dd className="font-medium text-stone-800">
              {formatWhen(record.atualizado_em)}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>Por</dt>
            <dd className="font-medium text-stone-800">
              {record.atualizado_por || '—'}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>Publicado em</dt>
            <dd className="font-medium text-stone-800">
              {formatWhen(record.publicado_em)}
            </dd>
          </div>
          <div className="flex justify-between gap-2">
            <dt>Persona</dt>
            <dd className="font-medium text-stone-800">
              {String((record.tree as { avatar_name?: string })?.avatar_name || '—')}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="text-xs text-stone-500">Nenhum registro neste status.</p>
      )}
    </div>
  );
}

export function CmsAssistenteChatEditor() {
  const { token } = useHubSession();
  const [sistemaDestino, setSistemaDestino] =
    useState<CmsSistemaDestino>('inove4us');
  const [rascunho, setRascunho] = useState<CmsAssistenteChatRecord | null>(null);
  const [publicado, setPublicado] = useState<CmsAssistenteChatRecord | null>(null);
  const [tree, setTree] = useState<AssistenteTree>(() =>
    normalizeTree(cloneAssistenteSeedInove4us())
  );
  const [jsonText, setJsonText] = useState(() =>
    prettyJson(normalizeTree(cloneAssistenteSeedInove4us()))
  );
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [editorTab, setEditorTab] = useState<EditorTab>('visual');
  const [selectedNodeId, setSelectedNodeId] = useState('inicio');
  const [navTrail, setNavTrail] = useState<string[]>(['inicio']);
  const [collapsedOutline, setCollapsedOutline] = useState<Set<string>>(
    () => new Set()
  );
  const [newNodeId, setNewNodeId] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<CmsPostStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveErrors, setSaveErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const jsonValid = !jsonError;

  const applyTreeToEditor = useCallback((incoming: AssistenteTree) => {
    const next = normalizeTree(incoming);
    setTree(next);
    setJsonText(prettyJson(next));
    setJsonError(null);
    const root =
      next.root_id && next.nodes[next.root_id]
        ? next.root_id
        : Object.keys(next.nodes)[0] || 'inicio';
    setSelectedNodeId(root);
    setNavTrail([root]);
    setCollapsedOutline(new Set());
  }, []);

  const commitTree = useCallback((next: AssistenteTree) => {
    const normalized = normalizeTree(next);
    setTree(normalized);
    setJsonText(prettyJson(normalized));
    setJsonError(null);
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setLoadError(null);
    setSaveErrors([]);
    try {
      const data = await fetchCmsAssistenteChatAdmin(token, sistemaDestino);
      setRascunho(data.rascunho);
      setPublicado(data.publicado);
      const source =
        (data.rascunho?.tree as AssistenteTree | undefined) ||
        (data.publicado?.tree as AssistenteTree | undefined) ||
        null;
      applyTreeToEditor(source || cloneAssistenteSeedInove4us());
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : 'Falha ao carregar');
      setRascunho(null);
      setPublicado(null);
    } finally {
      setLoading(false);
    }
  }, [token, sistemaDestino, applyTreeToEditor]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const nodeIds = useMemo(
    () => Object.keys(tree.nodes || {}).sort((a, b) => a.localeCompare(b)),
    [tree.nodes]
  );

  const reachable = useMemo(() => computeReachable(tree), [tree]);
  const orphanIds = useMemo(
    () => nodeIds.filter((id) => !reachable.has(id)),
    [nodeIds, reachable]
  );
  const outlineRows = useMemo(
    () => buildOutlineRows(tree, collapsedOutline),
    [tree, collapsedOutline]
  );

  const selectedNode: AssistenteTreeNode | null =
    selectedNodeId && tree.nodes[selectedNodeId]
      ? tree.nodes[selectedNodeId]
      : null;

  function selectNodeResetTrail(id: string) {
    setSelectedNodeId(id);
    setNavTrail([id]);
  }

  function navigateToNode(id: string) {
    if (!tree.nodes[id]) return;
    setSelectedNodeId(id);
    setNavTrail((prev) => {
      const idx = prev.indexOf(id);
      if (idx >= 0) return prev.slice(0, idx + 1);
      return [...prev, id];
    });
  }

  function jumpBreadcrumb(index: number) {
    const id = navTrail[index];
    if (!id || !tree.nodes[id]) return;
    setSelectedNodeId(id);
    setNavTrail(navTrail.slice(0, index + 1));
  }

  function toggleOutline(pathKey: string) {
    setCollapsedOutline((prev) => {
      const next = new Set(prev);
      if (next.has(pathKey)) next.delete(pathKey);
      else next.add(pathKey);
      return next;
    });
  }

  function syncPersona(name: string, tagline: string) {
    commitTree({
      ...tree,
      avatar_name: name,
      avatar_tagline: tagline,
      avatar_candidates: [name.trim() || 'Nina'],
    });
  }

  function onJsonChange(value: string) {
    setJsonText(value);
    const { tree: parsed, error } = tryParseTree(value);
    if (error || !parsed) {
      setJsonError(error || 'JSON inválido');
      return;
    }
    setJsonError(null);
    const next = normalizeTree(parsed);
    setTree(next);
    if (selectedNodeId && !next.nodes[selectedNodeId]) {
      const fallback =
        next.root_id in next.nodes
          ? next.root_id
          : Object.keys(next.nodes)[0] || '';
      setSelectedNodeId(fallback);
      setNavTrail(fallback ? [fallback] : []);
    }
  }

  function switchTab(next: EditorTab) {
    if (next === 'visual' && jsonError) {
      setToast('Corrija o JSON inválido antes de usar a aba Visual.');
      return;
    }
    if (next === 'json') {
      setJsonText(prettyJson(tree));
      setJsonError(null);
    }
    // Trocar de aba reinicia o breadcrumb a partir do nó atual
    if (selectedNodeId) setNavTrail([selectedNodeId]);
    setEditorTab(next);
  }

  function loadSeed() {
    applyTreeToEditor(cloneAssistenteSeedInove4us());
    setSaveErrors([]);
    setToast('Árvore inicial inove4us carregada no editor (ainda não salva).');
  }

  function updateSelectedNode(patch: Partial<AssistenteTreeNode>) {
    if (!selectedNodeId || !selectedNode) return;
    commitTree({
      ...tree,
      nodes: {
        ...tree.nodes,
        [selectedNodeId]: { ...selectedNode, ...patch },
      },
    });
  }

  function updateOption(idx: number, patch: Partial<AssistenteTreeOption>) {
    if (!selectedNode) return;
    const options = selectedNode.options.map((opt, i) => {
      if (i !== idx) return opt;
      const next: AssistenteTreeOption = { ...opt, ...patch };
      if ('next' in patch) {
        const v = String(patch.next ?? '').trim();
        if (!v) delete next.next;
        else next.next = v;
      }
      if ('href' in patch) {
        const v = String(patch.href ?? '').trim();
        if (!v) delete next.href;
        else next.href = v;
      }
      if ('action' in patch) {
        const v = String(patch.action ?? '').trim();
        if (!v) delete next.action;
        else next.action = v;
      }
      return next;
    });
    updateSelectedNode({ options });
  }

  function addOption() {
    if (!selectedNode) return;
    updateSelectedNode({
      options: [...selectedNode.options, { label: '' }],
    });
  }

  function removeOption(idx: number) {
    if (!selectedNode) return;
    updateSelectedNode({
      options: selectedNode.options.filter((_, i) => i !== idx),
    });
  }

  function addNode() {
    const id = newNodeId.trim().toLowerCase();
    if (!NODE_ID_RE.test(id)) {
      setToast('ID inválido. Use letras minúsculas, números e _ (ex.: novo_topico).');
      return;
    }
    if (tree.nodes[id]) {
      setToast(`Já existe um nó com id "${id}".`);
      return;
    }
    commitTree({
      ...tree,
      nodes: {
        ...tree.nodes,
        [id]: { message: '', options: [] },
      },
    });
    selectNodeResetTrail(id);
    setNewNodeId('');
    setToast(`Nó "${id}" adicionado.`);
  }

  function removeNode() {
    if (!selectedNodeId) return;
    if (selectedNodeId === tree.root_id) {
      setToast('Não é possível remover o nó raiz (root_id). Altere root_id no JSON antes.');
      return;
    }
    const refs = inboundRefs(tree, selectedNodeId);
    const warn =
      refs.length > 0
        ? `Atenção: ${refs.length} opção(ões) apontam para "${selectedNodeId}" (${refs.slice(0, 3).join(', ')}${refs.length > 3 ? '…' : ''}). Remover mesmo assim?`
        : `Remover o nó "${selectedNodeId}"?`;
    if (!window.confirm(warn)) return;
    const nodes = { ...tree.nodes };
    delete nodes[selectedNodeId];
    const nextRoot =
      tree.root_id in nodes
        ? tree.root_id
        : Object.keys(nodes)[0] || tree.root_id;
    commitTree({ ...tree, nodes, root_id: nextRoot });
    selectNodeResetTrail(nextRoot);
  }

  async function save(status: CmsPostStatus) {
    if (!token) return;
    if (!jsonValid) {
      setSaveErrors(['JSON inválido — corrija antes de salvar.']);
      return;
    }
    const clientErrors = validateTreeClient(tree);
    if (status === 'publicado' && clientErrors.length) {
      setSaveErrors(clientErrors);
      return;
    }
    // href inválido também bloqueia rascunho no client (pedido do prompt)
    const hrefErrors = clientErrors.filter((e) => e.includes('.href'));
    if (hrefErrors.length) {
      setSaveErrors(hrefErrors);
      return;
    }

    setSaving(status);
    setSaveErrors([]);
    try {
      const payload: AssistenteTree = {
        ...tree,
        avatar_name: tree.avatar_name.trim() || 'Nina',
        avatar_tagline: tree.avatar_tagline.trim() || 'Guia do inovador',
      };
      await saveCmsAssistenteChat(token, {
        sistema_destino: sistemaDestino,
        status,
        tree: payload as unknown as Record<string, unknown>,
      });
      setToast(status === 'publicado' ? 'Publicado com sucesso.' : 'Rascunho salvo.');
      await load();
    } catch (err) {
      setSaveErrors(extractApiErrors(err));
    } finally {
      setSaving(null);
    }
  }

  const previewRoot = useMemo(() => {
    const rootId = String(tree.root_id || '').trim();
    const node = tree.nodes?.[rootId];
    if (!node) return null;
    return { rootId, message: String(node.message || ''), options: node.options || [] };
  }, [tree]);

  const field =
    'w-full rounded-xl border border-stone-300 bg-white px-3 py-2.5 text-sm text-stone-800 outline-none ring-orange-400/30 transition focus:border-orange-400 focus:ring-2';

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/dashboard/cms"
            className="mb-2 inline-flex items-center gap-1.5 text-xs font-semibold text-stone-500 hover:text-stone-800"
          >
            <ArrowLeft className="size-3.5" aria-hidden />
            Voltar ao CMS
          </Link>
          <div className="mb-1 flex items-center gap-2">
            <Bot className="size-5 text-orange-500" aria-hidden />
            <h1 className="text-xl font-bold text-stone-900">
              Assistente Nina
            </h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Edite a árvore no modo Visual ou em JSON — o mesmo estado alimenta
            rascunho e publicação.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <RefreshCw className="size-4" aria-hidden />
            Atualizar
          </button>
          <button
            type="button"
            onClick={loadSeed}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
          >
            <Sparkles className="size-4" aria-hidden />
            Carregar árvore inicial inove4us
          </button>
        </div>
      </div>

      {toast ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {toast}
        </div>
      ) : null}

      {loadError ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {loadError}
        </div>
      ) : null}

      {saveErrors.length > 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <p className="mb-1 font-semibold">Erros de validação</p>
          <ul className="list-disc space-y-1 pl-5">
            {saveErrors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <label className="block space-y-1.5">
          <span className="text-xs font-bold uppercase tracking-wide text-stone-500">
            Sistema destino
          </span>
          <select
            className={field}
            value={sistemaDestino}
            onChange={(e) =>
              setSistemaDestino(e.target.value as CmsSistemaDestino)
            }
          >
            {DESTINOS_MVP.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </label>
        <StatusCard title="Rascunho" record={rascunho} />
        <StatusCard title="Publicado" record={publicado} />
      </div>

      {loading ? (
        <div className="flex justify-center py-16 text-stone-500">
          <Loader2 className="size-6 animate-spin" aria-hidden />
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
            <h2 className="mb-3 text-sm font-bold text-stone-900">Persona</h2>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="block space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wide text-stone-500">
                  avatar_name
                </span>
                <input
                  className={field}
                  value={tree.avatar_name}
                  onChange={(e) =>
                    syncPersona(e.target.value, tree.avatar_tagline)
                  }
                  placeholder="Nina"
                />
              </label>
              <label className="block space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wide text-stone-500">
                  avatar_tagline
                </span>
                <input
                  className={field}
                  value={tree.avatar_tagline}
                  onChange={(e) =>
                    syncPersona(tree.avatar_name, e.target.value)
                  }
                  placeholder="Guia do inovador"
                />
              </label>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
            <div className="space-y-3">
              <div className="flex gap-2 border-b border-stone-200">
                {(
                  [
                    ['visual', 'Visual'],
                    ['json', 'JSON'],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={editorTab === id}
                    onClick={() => switchTab(id)}
                    className={`px-3 py-2 text-sm font-semibold transition ${
                      editorTab === id
                        ? 'border-b-2 border-orange-500 text-orange-700'
                        : 'text-stone-500 hover:text-stone-800'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {editorTab === 'json' ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-sm font-bold text-stone-900">
                      Editor JSON (tree)
                    </h2>
                    <span
                      className={`text-xs font-semibold ${
                        jsonValid ? 'text-emerald-700' : 'text-red-600'
                      }`}
                    >
                      {jsonValid ? 'JSON válido' : jsonError || 'JSON inválido'}
                    </span>
                  </div>
                  <textarea
                    value={jsonText}
                    onChange={(e) => onJsonChange(e.target.value)}
                    spellCheck={false}
                    className="min-h-[520px] w-full rounded-2xl border border-stone-300 bg-white p-3 font-mono text-xs leading-relaxed text-stone-800 outline-none ring-orange-400/30 transition focus:border-orange-400 focus:ring-2"
                  />
                </div>
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
                  <div className="space-y-3 rounded-2xl border border-stone-200 bg-white p-3">
                    <div>
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <h2 className="text-sm font-bold text-stone-900">
                          Árvore
                        </h2>
                        <span className="text-[11px] text-stone-400">
                          a partir de {tree.root_id}
                        </span>
                      </div>
                      <ul className="max-h-[220px] space-y-0.5 overflow-y-auto">
                        {outlineRows.length === 0 ? (
                          <li className="px-1 py-2 text-xs text-stone-500">
                            root_id inválido — sem árvore.
                          </li>
                        ) : (
                          outlineRows.map((row) => {
                            const active = row.id === selectedNodeId;
                            const collapsed = collapsedOutline.has(row.pathKey);
                            return (
                              <li key={row.pathKey}>
                                <div
                                  className={`flex items-start gap-0.5 rounded-lg ${
                                    active
                                      ? 'bg-orange-50 ring-1 ring-orange-200'
                                      : 'hover:bg-stone-50'
                                  }`}
                                  style={{ paddingLeft: `${row.depth * 12}px` }}
                                >
                                  <button
                                    type="button"
                                    className="mt-1.5 shrink-0 rounded p-0.5 text-stone-400 hover:text-stone-700 disabled:opacity-0"
                                    disabled={!row.hasChildren}
                                    aria-label={collapsed ? 'Expandir' : 'Recolher'}
                                    onClick={() => toggleOutline(row.pathKey)}
                                  >
                                    {row.hasChildren ? (
                                      collapsed ? (
                                        <ChevronRight className="size-3.5" />
                                      ) : (
                                        <ChevronDown className="size-3.5" />
                                      )
                                    ) : (
                                      <span className="inline-block size-3.5" />
                                    )}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => selectNodeResetTrail(row.id)}
                                    className="min-w-0 flex-1 px-1 py-1.5 text-left"
                                  >
                                    <span
                                      className={`block truncate font-mono text-[11px] font-semibold ${
                                        active
                                          ? 'text-orange-800'
                                          : 'text-stone-800'
                                      }`}
                                    >
                                      {row.id}
                                      {row.id === tree.root_id ? ' · início' : ''}
                                    </span>
                                    <span className="block truncate text-[10px] text-stone-500">
                                      {row.messagePreview}
                                    </span>
                                  </button>
                                </div>
                              </li>
                            );
                          })
                        )}
                      </ul>
                    </div>

                    <div className="border-t border-stone-100 pt-3">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <h2 className="text-sm font-bold text-stone-900">
                          Lista
                        </h2>
                        <span className="text-[11px] text-stone-400">
                          {nodeIds.length}
                        </span>
                      </div>
                      <ul className="max-h-[160px] space-y-1 overflow-y-auto">
                        {nodeIds.map((id) => {
                          const isRoot = id === tree.root_id;
                          const active = id === selectedNodeId;
                          const orphan = orphanIds.includes(id);
                          return (
                            <li key={id}>
                              <button
                                type="button"
                                onClick={() => selectNodeResetTrail(id)}
                                className={`flex w-full items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-left text-sm transition ${
                                  active
                                    ? 'bg-orange-50 font-semibold text-orange-800 ring-1 ring-orange-200'
                                    : 'text-stone-700 hover:bg-stone-50'
                                }`}
                              >
                                <span className="truncate font-mono text-xs">
                                  {id}
                                </span>
                                <span className="flex shrink-0 items-center gap-1">
                                  {orphan ? (
                                    <span className="rounded-full bg-amber-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800 ring-1 ring-amber-200">
                                      órfão
                                    </span>
                                  ) : null}
                                  {isRoot ? (
                                    <span className="rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-700 ring-1 ring-emerald-200">
                                      início
                                    </span>
                                  ) : null}
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    </div>

                    {orphanIds.length > 0 ? (
                      <div className="rounded-xl border border-amber-200 bg-amber-50/80 p-2.5">
                        <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-amber-800">
                          Nós não conectados ({orphanIds.length})
                        </p>
                        <p className="mb-2 text-[10px] text-amber-800/80">
                          Existem em nodes, mas não são alcançáveis a partir de{' '}
                          <span className="font-mono">{tree.root_id}</span>.
                          Aviso informativo — não bloqueia salvar.
                        </p>
                        <ul className="space-y-1">
                          {orphanIds.map((id) => (
                            <li key={id}>
                              <button
                                type="button"
                                onClick={() => selectNodeResetTrail(id)}
                                className="w-full rounded-lg bg-white/70 px-2 py-1 text-left font-mono text-[11px] font-semibold text-amber-900 ring-1 ring-amber-200 hover:bg-white"
                              >
                                {id}
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    <div className="space-y-2 border-t border-stone-100 pt-3">
                      <input
                        className={field}
                        value={newNodeId}
                        onChange={(e) => setNewNodeId(e.target.value)}
                        placeholder="novo_node_id"
                      />
                      <button
                        type="button"
                        onClick={addNode}
                        className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs font-bold text-stone-800 hover:bg-stone-50"
                      >
                        <Plus className="size-3.5" aria-hidden />
                        Adicionar nó
                      </button>
                      <button
                        type="button"
                        onClick={removeNode}
                        disabled={!selectedNodeId || selectedNodeId === tree.root_id}
                        className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-bold text-red-700 hover:bg-red-100 disabled:opacity-40"
                      >
                        <Trash2 className="size-3.5" aria-hidden />
                        Remover nó
                      </button>
                    </div>
                  </div>

                  <div className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4">
                    {!selectedNode ? (
                      <p className="text-sm text-stone-500">
                        Selecione um nó na lista.
                      </p>
                    ) : (
                      <>
                        <nav
                          aria-label="Caminho na árvore"
                          className="flex flex-wrap items-center gap-1 text-xs text-stone-500"
                        >
                          {navTrail.map((id, index) => (
                            <span key={`${id}-${index}`} className="flex items-center gap-1">
                              {index > 0 ? (
                                <span className="text-stone-300" aria-hidden>
                                  ›
                                </span>
                              ) : null}
                              <button
                                type="button"
                                onClick={() => jumpBreadcrumb(index)}
                                className={`rounded px-1 py-0.5 font-mono font-semibold transition ${
                                  index === navTrail.length - 1
                                    ? 'bg-stone-100 text-stone-900'
                                    : 'text-orange-700 hover:bg-orange-50'
                                }`}
                              >
                                {id}
                              </button>
                            </span>
                          ))}
                        </nav>

                        <div>
                          <p className="text-xs font-bold uppercase tracking-wide text-stone-500">
                            Editando
                          </p>
                          <p className="font-mono text-sm font-semibold text-stone-900">
                            {selectedNodeId}
                            {orphanIds.includes(selectedNodeId) ? (
                              <span className="ml-2 align-middle text-[10px] font-bold uppercase tracking-wide text-amber-700">
                                não conectado
                              </span>
                            ) : null}
                          </p>
                        </div>
                        <label className="block space-y-1.5">
                          <span className="text-xs font-bold uppercase tracking-wide text-stone-500">
                            Mensagem
                          </span>
                          <textarea
                            className={`${field} min-h-[140px] leading-relaxed`}
                            value={selectedNode.message}
                            onChange={(e) =>
                              updateSelectedNode({ message: e.target.value })
                            }
                          />
                        </label>

                        <div className="space-y-3">
                          <div className="flex items-center justify-between gap-2">
                            <h3 className="text-sm font-bold text-stone-900">
                              Opções
                            </h3>
                            <button
                              type="button"
                              onClick={addOption}
                              className="inline-flex items-center gap-1.5 rounded-lg border border-stone-300 px-2.5 py-1.5 text-xs font-bold text-stone-700 hover:bg-stone-50"
                            >
                              <Plus className="size-3.5" aria-hidden />
                              Adicionar opção
                            </button>
                          </div>

                          {selectedNode.options.length === 0 ? (
                            <p className="text-xs text-stone-500">
                              Nenhuma opção (nó terminal).
                            </p>
                          ) : (
                            selectedNode.options.map((opt, idx) => {
                              const href = String(opt.href || '');
                              const hrefInvalid =
                                href.trim() !== '' && !href.trim().startsWith('/');
                              const nextId = String(opt.next || '').trim();
                              const nextExists = nextId
                                ? !!tree.nodes[nextId]
                                : false;
                              return (
                                <div
                                  key={idx}
                                  className="space-y-2 rounded-xl border border-stone-200 bg-stone-50 p-3"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <span className="text-xs font-bold text-stone-500">
                                      Opção {idx + 1}
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => removeOption(idx)}
                                      className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:text-red-700"
                                    >
                                      <Trash2 className="size-3.5" aria-hidden />
                                      Remover
                                    </button>
                                  </div>
                                  <label className="block space-y-1">
                                    <span className="text-[11px] font-semibold text-stone-500">
                                      Label
                                    </span>
                                    <input
                                      className={field}
                                      value={opt.label || ''}
                                      onChange={(e) =>
                                        updateOption(idx, { label: e.target.value })
                                      }
                                    />
                                  </label>
                                  <div className="space-y-1.5">
                                    <div className="flex flex-wrap items-end gap-2">
                                      <label className="min-w-[10rem] flex-1 space-y-1">
                                        <span className="text-[11px] font-semibold text-stone-500">
                                          Próximo nó
                                        </span>
                                        <select
                                          className={field}
                                          value={opt.next || ''}
                                          onChange={(e) =>
                                            updateOption(idx, {
                                              next: e.target.value,
                                            })
                                          }
                                        >
                                          <option value="">(nenhum)</option>
                                          {nodeIds.map((id) => (
                                            <option key={id} value={id}>
                                              {id}
                                              {id === tree.root_id
                                                ? ' (início)'
                                                : ''}
                                            </option>
                                          ))}
                                        </select>
                                      </label>
                                      {nextId && nextExists ? (
                                        <button
                                          type="button"
                                          onClick={() => navigateToNode(nextId)}
                                          className="inline-flex items-center gap-1 rounded-xl border border-orange-200 bg-orange-50 px-3 py-2.5 text-xs font-bold text-orange-800 hover:bg-orange-100"
                                        >
                                          Ir para nó
                                          <ArrowRight className="size-3.5" aria-hidden />
                                        </button>
                                      ) : null}
                                    </div>
                                    {nextId ? (
                                      nextExists ? (
                                        <p className="rounded-lg bg-white px-2.5 py-2 text-[11px] leading-snug text-stone-600 ring-1 ring-stone-200">
                                          <span className="font-semibold text-stone-500">
                                            Preview:{' '}
                                          </span>
                                          {snippetMessage(
                                            tree.nodes[nextId].message || ''
                                          )}
                                        </p>
                                      ) : (
                                        <p className="text-xs font-semibold text-red-600">
                                          nó inexistente: {nextId}
                                        </p>
                                      )
                                    ) : null}
                                  </div>
                                  <label className="block space-y-1">
                                    <span className="text-[11px] font-semibold text-stone-500">
                                      Link (href)
                                    </span>
                                    <input
                                      className={`${field} ${
                                        hrefInvalid
                                          ? 'border-red-400 focus:border-red-400 focus:ring-red-300/40'
                                          : ''
                                      }`}
                                      value={href}
                                      placeholder="/rota-interna"
                                      onChange={(e) =>
                                        updateOption(idx, { href: e.target.value })
                                      }
                                    />
                                    {hrefInvalid ? (
                                      <span className="text-xs text-red-600">
                                        href deve começar com &quot;/&quot;
                                      </span>
                                    ) : null}
                                  </label>
                                  <label className="block space-y-1">
                                    <span className="text-[11px] font-semibold text-stone-500">
                                      Ação (action)
                                    </span>
                                    <select
                                      className={field}
                                      value={opt.action || ''}
                                      onChange={(e) =>
                                        updateOption(idx, { action: e.target.value })
                                      }
                                    >
                                      {ACTION_WHITELIST.map((a) => (
                                        <option key={a || 'empty'} value={a}>
                                          {a || '(nenhuma)'}
                                        </option>
                                      ))}
                                    </select>
                                  </label>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <h2 className="text-sm font-bold text-stone-900">Preview (raiz)</h2>
              <div className="min-h-[280px] rounded-2xl border border-stone-200 bg-white p-4 xl:min-h-[520px]">
                {!previewRoot ? (
                  <p className="text-sm text-stone-500">
                    Defina um root_id válido para ver o preview.
                  </p>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 text-sm font-bold text-orange-700">
                        {(tree.avatar_name || 'N').slice(0, 1).toUpperCase()}
                      </span>
                      <div>
                        <p className="font-bold text-stone-900">
                          {tree.avatar_name || 'Nina'}
                        </p>
                        <p className="text-xs text-stone-500">
                          {tree.avatar_tagline || 'Guia do inovador'}
                        </p>
                      </div>
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-stone-700">
                      {previewRoot.message}
                    </p>
                    <div className="flex flex-col gap-2">
                      {previewRoot.options.map((opt, idx) => (
                        <button
                          key={`${opt.label}-${idx}`}
                          type="button"
                          disabled
                          className="rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-left text-sm font-semibold text-stone-700"
                        >
                          {opt.label}
                          {opt.href ? (
                            <span className="mt-0.5 block text-[11px] font-normal text-stone-400">
                              href: {opt.href}
                            </span>
                          ) : null}
                          {opt.action ? (
                            <span className="mt-0.5 block text-[11px] font-normal text-stone-400">
                              action: {opt.action}
                            </span>
                          ) : null}
                        </button>
                      ))}
                    </div>
                    <p className="text-[11px] text-stone-400">
                      root_id: {previewRoot.rootId} · preview estático
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={!jsonValid || saving !== null}
              onClick={() => void save('rascunho')}
              className="inline-flex items-center gap-2 rounded-xl border border-stone-300 bg-white px-4 py-2.5 text-sm font-bold text-stone-800 transition hover:bg-stone-50 disabled:opacity-50"
            >
              {saving === 'rascunho' ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Save className="size-4" aria-hidden />
              )}
              Salvar rascunho
            </button>
            <button
              type="button"
              disabled={!jsonValid || saving !== null}
              onClick={() => void save('publicado')}
              className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-orange-400 disabled:opacity-50"
            >
              {saving === 'publicado' ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Upload className="size-4" aria-hidden />
              )}
              Publicar
            </button>
          </div>
        </>
      )}
    </div>
  );
}
