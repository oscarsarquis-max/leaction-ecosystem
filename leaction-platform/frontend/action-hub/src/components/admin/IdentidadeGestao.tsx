'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { IdCard, Loader2, Pencil, Plus, RefreshCw, X } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import {
  createIdentidadePermissao,
  fetchAdminApps,
  fetchIdentidadeFuncoes,
  fetchIdentidadePermissoes,
  fetchIdentidadeUsuarios,
  IDENTIDADE_NIVEIS,
  parseAdminApiErrors,
  updateIdentidadeUsuario,
  upsertIdentidadeFuncao,
  type AdminApp,
  type IdentidadeFuncao,
  type IdentidadeNivel,
  type IdentidadePermissao,
  type IdentidadeStatus,
  type IdentidadeUsuario,
} from '@/lib/admin-api';

type TabId = 'usuarios' | 'funcoes' | 'permissoes';

const PILOTO_APP_ID = 'phanton';

const NIVEL_LABEL: Record<IdentidadeNivel, string> = {
  admin: 'Administrador',
  gestor_produtivo: 'Gestor produtivo',
  usuario_executor: 'Usuário executor',
};

function nivelLabel(nivel: string) {
  return NIVEL_LABEL[nivel as IdentidadeNivel] || nivel;
}

function statusLabel(status: string) {
  if (status === 'ativo') return 'Ativo';
  if (status === 'inativo') return 'Inativo';
  return status;
}

const fieldClass =
  'rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-medium text-stone-800 outline-none ring-emerald-200 focus:ring-2';

function ErrorList({ messages }: { messages: string[] }) {
  if (!messages.length) return null;
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
      {messages.length === 1 ? (
        <p>{messages[0]}</p>
      ) : (
        <ul className="list-disc space-y-1 pl-5">
          {messages.map((msg) => (
            <li key={msg}>{msg}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function mergeSistemas(apps: AdminApp[]): AdminApp[] {
  const byId = new Map(apps.map((app) => [app.app_id, app]));
  if (!byId.has(PILOTO_APP_ID)) {
    byId.set(PILOTO_APP_ID, {
      app_id: PILOTO_APP_ID,
      name: 'Phanton',
      webhook_url: null,
      return_origins: [],
      active: true,
      has_secret: false,
      secret_hint: null,
    });
  }
  return [...byId.values()].sort((a, b) => {
    if (a.app_id === PILOTO_APP_ID) return -1;
    if (b.app_id === PILOTO_APP_ID) return 1;
    return a.name.localeCompare(b.name, 'pt-BR');
  });
}

type Props = {
  initialSistema?: string;
};

export function IdentidadeGestao({ initialSistema = '' }: Props) {
  const { token } = useHubSession();
  const router = useRouter();
  const [apps, setApps] = useState<AdminApp[]>([]);
  const [sistema, setSistema] = useState(initialSistema);
  const [tab, setTab] = useState<TabId>('usuarios');
  const [usuarios, setUsuarios] = useState<IdentidadeUsuario[]>([]);
  const [funcoes, setFuncoes] = useState<IdentidadeFuncao[]>([]);
  const [permissoes, setPermissoes] = useState<IdentidadePermissao[]>([]);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);
  const [success, setSuccess] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<IdentidadeUsuario | null>(null);

  const [fnNome, setFnNome] = useState('');
  const [fnNivel, setFnNivel] = useState<IdentidadeNivel>('usuario_executor');
  const [fnPerms, setFnPerms] = useState<string[]>([]);
  const [fnSaving, setFnSaving] = useState(false);

  const [permChave, setPermChave] = useState('');
  const [permDescricao, setPermDescricao] = useState('');
  const [permSaving, setPermSaving] = useState(false);

  useEffect(() => {
    setSistema(initialSistema);
  }, [initialSistema]);

  const sistemas = useMemo(() => mergeSistemas(apps), [apps]);

  const loadApps = useCallback(async () => {
    if (!token) return;
    try {
      const rows = await fetchAdminApps(token);
      setApps(rows);
    } catch (err) {
      setErrors(parseAdminApiErrors(err));
    }
  }, [token]);

  const loadCatalogo = useCallback(async () => {
    if (!token || !sistema) {
      setUsuarios([]);
      setFuncoes([]);
      setPermissoes([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setErrors([]);
    try {
      const [users, fns, perms] = await Promise.all([
        fetchIdentidadeUsuarios(token, sistema),
        fetchIdentidadeFuncoes(token, sistema),
        fetchIdentidadePermissoes(token, sistema),
      ]);
      setUsuarios(users);
      setFuncoes(fns);
      setPermissoes(perms);
    } catch (err) {
      setErrors(parseAdminApiErrors(err));
      setUsuarios([]);
      setFuncoes([]);
      setPermissoes([]);
    } finally {
      setLoading(false);
    }
  }, [token, sistema]);

  useEffect(() => {
    void loadApps();
  }, [loadApps]);

  useEffect(() => {
    if (sistema || sistemas.length === 0) return;
    const preferred =
      sistemas.find((app) => app.app_id === PILOTO_APP_ID)?.app_id ||
      sistemas[0]?.app_id;
    if (preferred) setSistema(preferred);
  }, [sistemas, sistema]);

  useEffect(() => {
    void loadCatalogo();
  }, [loadCatalogo]);

  function selectSistema(next: string) {
    setSistema(next);
    setSuccess(null);
    setErrors([]);
    const params = new URLSearchParams();
    if (next) params.set('sistema', next);
    router.replace(
      `/dashboard/identidade${params.toString() ? `?${params}` : ''}`
    );
  }

  function fillFuncaoForm(fn: IdentidadeFuncao | null) {
    if (!fn) {
      setFnNome('');
      setFnNivel('usuario_executor');
      setFnPerms([]);
      return;
    }
    setFnNome(fn.nome);
    setFnNivel(
      IDENTIDADE_NIVEIS.includes(fn.nivel_associado as IdentidadeNivel)
        ? (fn.nivel_associado as IdentidadeNivel)
        : 'usuario_executor'
    );
    setFnPerms(Array.isArray(fn.permissoes) ? fn.permissoes : []);
  }

  async function handleSaveFuncao(event: FormEvent) {
    event.preventDefault();
    if (!token || !sistema) return;
    setFnSaving(true);
    setErrors([]);
    setSuccess(null);
    try {
      await upsertIdentidadeFuncao(token, {
        sistema,
        nome: fnNome.trim(),
        nivel_associado: fnNivel,
        permissoes: fnPerms,
      });
      setSuccess(`Função “${fnNome.trim()}” gravada.`);
      fillFuncaoForm(null);
      await loadCatalogo();
    } catch (err) {
      setErrors(parseAdminApiErrors(err));
    } finally {
      setFnSaving(false);
    }
  }

  async function handleCreatePermissao(event: FormEvent) {
    event.preventDefault();
    if (!token || !sistema) return;
    setPermSaving(true);
    setErrors([]);
    setSuccess(null);
    try {
      await createIdentidadePermissao(token, {
        sistema,
        chave: permChave.trim(),
        descricao: permDescricao.trim(),
      });
      setSuccess(`Permissão “${permChave.trim()}” criada.`);
      setPermChave('');
      setPermDescricao('');
      await loadCatalogo();
    } catch (err) {
      setErrors(parseAdminApiErrors(err));
    } finally {
      setPermSaving(false);
    }
  }

  const selectedName =
    sistemas.find((app) => app.app_id === sistema)?.name || sistema;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <IdCard className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold tracking-tight text-stone-900 md:text-2xl">
              Gestão de Identidade
            </h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Catálogo de nível, função e permissões dos satélites. O login do
            usuário final continua em cada sistema
            {selectedName ? (
              <>
                {' '}
                · <span className="font-semibold text-stone-700">{selectedName}</span>
              </>
            ) : null}
            .
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadCatalogo()}
          disabled={loading || !sistema}
          className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:opacity-60"
        >
          {loading ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <RefreshCw className="size-4" aria-hidden />
          )}
          Atualizar
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-stone-200 bg-stone-50/80 px-3 py-3">
        <label className="flex min-w-[14rem] flex-1 flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            Sistema
          </span>
          <select
            value={sistema}
            onChange={(e) => selectSistema(e.target.value)}
            className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-800 outline-none ring-emerald-200 focus:ring-2"
          >
            {sistemas.length === 0 ? (
              <option value="">Carregando sistemas…</option>
            ) : (
              sistemas.map((app) => (
                <option key={app.app_id} value={app.app_id}>
                  {app.name} ({app.app_id})
                </option>
              ))
            )}
          </select>
        </label>
      </div>

      <div className="flex gap-2 border-b border-stone-200" role="tablist">
        {(
          [
            ['usuarios', 'Usuários'],
            ['funcoes', 'Funções'],
            ['permissoes', 'Permissões'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => {
              setTab(id);
              setErrors([]);
            }}
            className={`px-3 py-2 text-sm font-semibold transition ${
              tab === id
                ? 'border-b-2 border-emerald-500 text-emerald-700'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {success ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {success}
        </div>
      ) : null}
      <ErrorList messages={errors} />

      {tab === 'usuarios' ? (
        <UsuariosSection
          loading={loading}
          usuarios={usuarios}
          onEdit={(user) => {
            setSuccess(null);
            setErrors([]);
            setEditingUser(user);
          }}
        />
      ) : null}

      {tab === 'funcoes' ? (
        <FuncoesSection
          loading={loading}
          funcoes={funcoes}
          permissoes={permissoes}
          fnNome={fnNome}
          fnNivel={fnNivel}
          fnPerms={fnPerms}
          fnSaving={fnSaving}
          onNome={setFnNome}
          onNivel={setFnNivel}
          onTogglePerm={(chave) =>
            setFnPerms((prev) =>
              prev.includes(chave)
                ? prev.filter((item) => item !== chave)
                : [...prev, chave]
            )
          }
          onPick={fillFuncaoForm}
          onSubmit={handleSaveFuncao}
        />
      ) : null}

      {tab === 'permissoes' ? (
        <PermissoesSection
          loading={loading}
          permissoes={permissoes}
          chave={permChave}
          descricao={permDescricao}
          saving={permSaving}
          onChave={setPermChave}
          onDescricao={setPermDescricao}
          onSubmit={handleCreatePermissao}
        />
      ) : null}

      <UsuarioEditModal
        open={Boolean(editingUser)}
        token={token}
        usuario={editingUser}
        funcoes={funcoes}
        onClose={() => setEditingUser(null)}
        onSuccess={(message) => {
          setSuccess(message);
          setEditingUser(null);
          void loadCatalogo();
        }}
        onError={setErrors}
      />
    </div>
  );
}

function UsuariosSection({
  loading,
  usuarios,
  onEdit,
}: {
  loading: boolean;
  usuarios: IdentidadeUsuario[];
  onEdit: (usuario: IdentidadeUsuario) => void;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
            <tr>
              <th className="px-4 py-3">Nome</th>
              <th className="px-4 py-3">E-mail</th>
              <th className="px-4 py-3">Nível</th>
              <th className="px-4 py-3">Função</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-200 bg-white">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                  <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                </td>
              </tr>
            ) : usuarios.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-stone-500">
                  Nenhum usuário sincronizado neste sistema. Os satélites enviam
                  os perfis pela API.
                </td>
              </tr>
            ) : (
              usuarios.map((user) => (
                <tr key={user.id} className="hover:bg-stone-50/80">
                  <td className="px-4 py-3 font-semibold text-stone-900">
                    {user.nome}
                  </td>
                  <td className="px-4 py-3 text-stone-600">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-lg bg-stone-100 px-2 py-0.5 text-xs font-semibold text-stone-700 ring-1 ring-stone-200">
                      {nivelLabel(user.nivel)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-stone-600">
                    {user.funcao || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        user.status === 'ativo'
                          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200'
                          : 'bg-stone-100 text-stone-600 ring-1 ring-stone-200'
                      }`}
                    >
                      {statusLabel(user.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => onEdit(user)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 transition hover:bg-stone-50"
                    >
                      <Pencil className="size-3.5" aria-hidden />
                      Editar
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FuncoesSection({
  loading,
  funcoes,
  permissoes,
  fnNome,
  fnNivel,
  fnPerms,
  fnSaving,
  onNome,
  onNivel,
  onTogglePerm,
  onPick,
  onSubmit,
}: {
  loading: boolean;
  funcoes: IdentidadeFuncao[];
  permissoes: IdentidadePermissao[];
  fnNome: string;
  fnNivel: IdentidadeNivel;
  fnPerms: string[];
  fnSaving: boolean;
  onNome: (value: string) => void;
  onNivel: (value: IdentidadeNivel) => void;
  onTogglePerm: (chave: string) => void;
  onPick: (fn: IdentidadeFuncao | null) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <div className="space-y-5">
      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4"
      >
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-stone-900">
              Criar ou atualizar função
            </h2>
            <p className="mt-0.5 text-xs text-stone-500">
              Se o nome já existir neste sistema, o cadastro é atualizado.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onPick(null)}
            className="text-xs font-semibold text-stone-500 hover:text-stone-800"
          >
            Limpar formulário
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Nome
            </span>
            <input
              required
              value={fnNome}
              onChange={(e) => onNome(e.target.value)}
              className={fieldClass}
              placeholder="professor"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Nível associado
            </span>
            <select
              value={fnNivel}
              onChange={(e) => onNivel(e.target.value as IdentidadeNivel)}
              className={fieldClass}
            >
              {IDENTIDADE_NIVEIS.map((nivel) => (
                <option key={nivel} value={nivel}>
                  {nivelLabel(nivel)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <fieldset>
          <legend className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            Permissões
          </legend>
          {permissoes.length === 0 ? (
            <p className="text-sm text-stone-500">
              Nenhuma permissão neste sistema. Cadastre na aba Permissões.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {permissoes.map((perm) => (
                <label
                  key={perm.id}
                  className="flex items-start gap-2 rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-700"
                >
                  <input
                    type="checkbox"
                    checked={fnPerms.includes(perm.chave)}
                    onChange={() => onTogglePerm(perm.chave)}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="font-mono text-xs font-semibold">
                      {perm.chave}
                    </span>
                    {perm.descricao ? (
                      <span className="mt-0.5 block text-xs text-stone-500">
                        {perm.descricao}
                      </span>
                    ) : null}
                  </span>
                </label>
              ))}
            </div>
          )}
        </fieldset>
        <button
          type="submit"
          disabled={fnSaving || !fnNome.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {fnSaving ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="size-4" aria-hidden />
          )}
          Salvar função
        </button>
      </form>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Nível associado</th>
                <th className="px-4 py-3">Permissões</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                  </td>
                </tr>
              ) : funcoes.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-stone-500">
                    Nenhuma função cadastrada neste sistema.
                  </td>
                </tr>
              ) : (
                funcoes.map((fn) => (
                  <tr key={fn.id} className="hover:bg-stone-50/80">
                    <td className="px-4 py-3 font-semibold text-stone-900">
                      {fn.nome}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {nivelLabel(fn.nivel_associado)}
                    </td>
                    <td className="px-4 py-3 text-xs text-stone-500">
                      {fn.permissoes.length
                        ? fn.permissoes.join(', ')
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => onPick(fn)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 transition hover:bg-stone-50"
                      >
                        <Pencil className="size-3.5" aria-hidden />
                        Editar
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function PermissoesSection({
  loading,
  permissoes,
  chave,
  descricao,
  saving,
  onChave,
  onDescricao,
  onSubmit,
}: {
  loading: boolean;
  permissoes: IdentidadePermissao[];
  chave: string;
  descricao: string;
  saving: boolean;
  onChave: (value: string) => void;
  onDescricao: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <div className="space-y-5">
      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4"
      >
        <h2 className="text-sm font-bold text-stone-900">Nova permissão</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Chave
            </span>
            <input
              required
              value={chave}
              onChange={(e) => onChave(e.target.value)}
              className={`${fieldClass} font-mono`}
              placeholder="criar_aula"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Descrição
            </span>
            <input
              value={descricao}
              onChange={(e) => onDescricao(e.target.value)}
              className={fieldClass}
              placeholder="Criar aula neste sistema"
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={saving || !chave.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-emerald-400 disabled:opacity-60"
        >
          {saving ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <Plus className="size-4" aria-hidden />
          )}
          Criar permissão
        </button>
      </form>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-4 py-3">Chave</th>
                <th className="px-4 py-3">Descrição</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={2} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
                  </td>
                </tr>
              ) : permissoes.length === 0 ? (
                <tr>
                  <td colSpan={2} className="px-4 py-10 text-center text-stone-500">
                    Nenhuma permissão cadastrada neste sistema.
                  </td>
                </tr>
              ) : (
                permissoes.map((perm) => (
                  <tr key={perm.id} className="hover:bg-stone-50/80">
                    <td className="px-4 py-3 font-mono text-xs font-semibold text-stone-800">
                      {perm.chave}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {perm.descricao || '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function UsuarioEditModal({
  open,
  token,
  usuario,
  funcoes,
  onClose,
  onSuccess,
  onError,
}: {
  open: boolean;
  token: string | null;
  usuario: IdentidadeUsuario | null;
  funcoes: IdentidadeFuncao[];
  onClose: () => void;
  onSuccess: (message: string) => void;
  onError: (messages: string[]) => void;
}) {
  const [nivel, setNivel] = useState<IdentidadeNivel>('usuario_executor');
  const [funcao, setFuncao] = useState('');
  const [status, setStatus] = useState<IdentidadeStatus>('ativo');
  const [saving, setSaving] = useState(false);
  const [localErrors, setLocalErrors] = useState<string[]>([]);

  useEffect(() => {
    if (!open || !usuario) return;
    setLocalErrors([]);
    setNivel(
      IDENTIDADE_NIVEIS.includes(usuario.nivel as IdentidadeNivel)
        ? (usuario.nivel as IdentidadeNivel)
        : 'usuario_executor'
    );
    setFuncao(usuario.funcao || '');
    setStatus(usuario.status === 'inativo' ? 'inativo' : 'ativo');
  }, [open, usuario]);

  if (!open || !usuario) return null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!usuario) return;
    setSaving(true);
    setLocalErrors([]);
    try {
      if (!token) throw new Error('Sessão administrativa ausente.');
      await updateIdentidadeUsuario(token, usuario.id, {
        nivel,
        funcao: funcao || null,
        status,
      });
      onSuccess(`Perfil de ${usuario.email} atualizado.`);
    } catch (err) {
      const messages = parseAdminApiErrors(err);
      setLocalErrors(messages);
      onError(messages);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-stone-950/40 p-0 sm:items-center sm:p-4">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Fechar"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="identidade-user-edit-title"
        className="relative z-10 flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <div>
            <h2
              id="identidade-user-edit-title"
              className="text-lg font-bold text-stone-900"
            >
              Editar perfil
            </h2>
            <p className="mt-0.5 text-sm text-stone-500">{usuario.email}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100 hover:text-stone-700"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 overflow-y-auto px-5 py-4">
          <ErrorList messages={localErrors} />
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Nível
            </span>
            <select
              value={nivel}
              onChange={(e) => setNivel(e.target.value as IdentidadeNivel)}
              className={fieldClass}
            >
              {IDENTIDADE_NIVEIS.map((option) => (
                <option key={option} value={option}>
                  {nivelLabel(option)}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Função
            </span>
            <select
              value={funcao}
              onChange={(e) => setFuncao(e.target.value)}
              className={fieldClass}
            >
              <option value="">—</option>
              {funcoes.map((fn) => (
                <option key={fn.id} value={fn.nome}>
                  {fn.nome}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Status
            </span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as IdentidadeStatus)}
              className={fieldClass}
            >
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl border border-stone-200 px-4 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
            >
              {saving ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
              Salvar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
