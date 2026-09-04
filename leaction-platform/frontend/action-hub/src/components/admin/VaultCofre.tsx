'use client';

import { FormEvent, useCallback, useEffect, useId, useState, type ReactNode } from 'react';
import { Eye, EyeOff, KeyRound, Loader2, LogOut, Plus, RefreshCw, X } from 'lucide-react';
import {
  VAULT_TOKEN_KEY,
  confirmarVaultSecret,
  createVaultConta,
  createVaultSecret,
  fetchVaultContas,
  fetchVaultHistorico,
  fetchVaultSecrets,
  fetchVaultSistemas,
  parseVaultApiErrors,
  revelarVaultSecret,
  rotacionarVaultSecret,
  upsertVaultSistema,
  vaultLogin,
  VaultSessionExpiredError,
  type VaultContaNivel,
  type VaultSecretMeta,
  type VaultSistema,
} from '@/lib/vault-api';

const NIVEL_CONTA_LABEL: Record<VaultContaNivel, string> = {
  admin: 'Administrador',
  gestor_produtivo: 'Gestor produtivo',
  usuario_executor: 'Usuário executor',
};

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

function statusLabel(status: string) {
  if (status === 'ativo') return 'Ativo';
  if (status === 'pendente_aplicacao') return 'Pendente de aplicação';
  if (status === 'revogado') return 'Revogado';
  return status;
}

function statusClass(status: string) {
  if (status === 'ativo') return 'bg-emerald-50 text-emerald-700 ring-emerald-200';
  if (status === 'pendente_aplicacao') return 'bg-amber-50 text-amber-800 ring-amber-200';
  return 'bg-stone-100 text-stone-600 ring-stone-200';
}

function readStoredToken() {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem(VAULT_TOKEN_KEY) || '';
}

export function VaultCofre() {
  const [token, setToken] = useState('');
  const [booting, setBooting] = useState(true);
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [loginBusy, setLoginBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [success, setSuccess] = useState<string | null>(null);

  const [sistemas, setSistemas] = useState<VaultSistema[]>([]);
  const [sistema, setSistema] = useState('');
  const [painel, setPainel] = useState<'secrets' | 'contas'>('secrets');
  const [secrets, setSecrets] = useState<VaultSecretMeta[]>([]);
  const [contas, setContas] = useState<VaultSecretMeta[]>([]);
  const [loading, setLoading] = useState(false);

  const [sysNome, setSysNome] = useState('');
  const [sysUrl, setSysUrl] = useState('');
  const [sysSecret, setSysSecret] = useState('');
  const [sysAuto, setSysAuto] = useState(false);
  const [sysSaving, setSysSaving] = useState(false);

  const [secTipo, setSecTipo] = useState('');
  const [secValor, setSecValor] = useState('');
  const [secSaving, setSecSaving] = useState(false);
  const [showSecValor, setShowSecValor] = useState(false);
  const fieldUid = useId().replace(/:/g, '');
  const rotationUrlName = `vault-rotation-url-${fieldUid}`;
  const s2sChannelName = `vault-s2s-channel-${fieldUid}`;
  const secretTipoName = `vault-secret-tipo-${fieldUid}`;
  const secretValueName = `vault-secret-value-${fieldUid}`;
  const contaEmailName = `vault-conta-email-${fieldUid}`;
  const contaSenhaName = `vault-conta-senha-${fieldUid}`;
  const contaFuncaoName = `vault-conta-funcao-${fieldUid}`;

  const [contaEmail, setContaEmail] = useState('');
  const [contaNivel, setContaNivel] = useState<VaultContaNivel>('usuario_executor');
  const [contaFuncao, setContaFuncao] = useState('');
  const [contaSenha, setContaSenha] = useState('');
  const [showContaSenha, setShowContaSenha] = useState(false);
  const [contaSaving, setContaSaving] = useState(false);
  const [manualCreateConta, setManualCreateConta] = useState<{
    id: number;
    valor: string;
    email: string;
  } | null>(null);

  const [revealed, setRevealed] = useState<{ id: number; valor: string } | null>(null);
  const [manualRotate, setManualRotate] = useState<{
    id: number;
    valor: string;
  } | null>(null);
  const [historico, setHistorico] = useState<{
    tipo: string;
    versoes: VaultSecretMeta[];
  } | null>(null);

  const expireSession = useCallback(() => {
    sessionStorage.removeItem(VAULT_TOKEN_KEY);
    setToken('');
    setSecrets([]);
    setContas([]);
    setSistemas([]);
    setRevealed(null);
    setManualRotate(null);
    setManualCreateConta(null);
    setHistorico(null);
  }, []);

  const handleVaultError = useCallback(
    (err: unknown) => {
      if (err instanceof VaultSessionExpiredError) {
        expireSession();
        setErrors([err.message]);
        return;
      }
      setErrors(parseVaultApiErrors(err));
    },
    [expireSession]
  );

  const loadAll = useCallback(
    async (tok: string, selected?: string) => {
      setLoading(true);
      setErrors([]);
      try {
        const rows = await fetchVaultSistemas(tok);
        setSistemas(rows);
        const next = selected || sistema || rows[0]?.sistema || '';
        if (next && next !== sistema) setSistema(next);
        if (next) {
          const [secs, accs] = await Promise.all([
            fetchVaultSecrets(tok, next),
            fetchVaultContas(tok, next),
          ]);
          setSecrets(secs);
          setContas(accs);
        } else {
          setSecrets([]);
          setContas([]);
        }
      } catch (err) {
        handleVaultError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleVaultError, sistema]
  );

  useEffect(() => {
    const stored = readStoredToken();
    if (!stored) {
      setBooting(false);
      return;
    }
    setToken(stored);
    void loadAll(stored).finally(() => setBooting(false));
    // boot once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!token || !sistema) {
      setSecrets([]);
      setContas([]);
      return;
    }
    setLoading(true);
    Promise.all([fetchVaultSecrets(token, sistema), fetchVaultContas(token, sistema)])
      .then(([secs, accs]) => {
        setSecrets(secs);
        setContas(accs);
      })
      .catch(handleVaultError)
      .finally(() => setLoading(false));
  }, [token, sistema, handleVaultError]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setLoginBusy(true);
    setErrors([]);
    try {
      const data = await vaultLogin(email.trim(), senha);
      sessionStorage.setItem(VAULT_TOKEN_KEY, data.access_token);
      setToken(data.access_token);
      setSenha('');
      await loadAll(data.access_token);
    } catch (err) {
      setErrors(parseVaultApiErrors(err));
    } finally {
      setLoginBusy(false);
    }
  }

  async function handleSaveSistema(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSysSaving(true);
    setErrors([]);
    setSuccess(null);
    try {
      await upsertVaultSistema(token, {
        sistema: (sysNome || sistema).trim(),
        rotation_webhook_url: sysUrl.trim() || null,
        rotation_secret: sysSecret.trim() || null,
        suporta_rotacao_automatica: sysAuto,
      });
      setSysSecret('');
      setSuccess('Sistema gravado no cofre.');
      await loadAll(token, (sysNome || sistema).trim().toLowerCase());
    } catch (err) {
      handleVaultError(err);
    } finally {
      setSysSaving(false);
    }
  }

  async function handleCreateSecret(event: FormEvent) {
    event.preventDefault();
    if (!token || !sistema) return;
    setSecSaving(true);
    setErrors([]);
    setSuccess(null);
    try {
      await createVaultSecret(token, {
        sistema,
        tipo: secTipo.trim(),
        valor: secValor,
      });
      setSecTipo('');
      setSecValor('');
      setShowSecValor(false);
      setSuccess('Secret criado. O valor não fica visível na lista.');
      const [secs, accs] = await Promise.all([
        fetchVaultSecrets(token, sistema),
        fetchVaultContas(token, sistema),
      ]);
      setSecrets(secs);
      setContas(accs);
    } catch (err) {
      handleVaultError(err);
    } finally {
      setSecSaving(false);
    }
  }

  async function handleCreateConta(event: FormEvent) {
    event.preventDefault();
    if (!token || !sistema) return;
    setContaSaving(true);
    setErrors([]);
    setSuccess(null);
    setManualCreateConta(null);
    try {
      const data = await createVaultConta(token, {
        sistema,
        email: contaEmail.trim(),
        nivel: contaNivel,
        funcao: contaFuncao.trim() || undefined,
        senha: contaSenha.trim() || undefined,
      });
      setContaEmail('');
      setContaFuncao('');
      setContaSenha('');
      setShowContaSenha(false);
      const [secs, accs] = await Promise.all([
        fetchVaultSecrets(token, sistema),
        fetchVaultContas(token, sistema),
      ]);
      setSecrets(secs);
      setContas(accs);
      if (data.valor) {
        setManualCreateConta({
          id: data.secret.id,
          valor: data.valor,
          email: data.secret.usuario_email || contaEmail.trim(),
        });
      } else {
        setSuccess('Conta criada no satélite. A senha não é exibida aqui.');
      }
    } catch (err) {
      handleVaultError(err);
    } finally {
      setContaSaving(false);
    }
  }

  async function handleRevelar(id: number) {
    if (!token) return;
    setErrors([]);
    try {
      const data = await revelarVaultSecret(token, id);
      setRevealed({ id, valor: data.valor });
    } catch (err) {
      handleVaultError(err);
    }
  }

  async function handleRotacionar(id: number) {
    if (!token) return;
    setErrors([]);
    setSuccess(null);
    try {
      const data = await rotacionarVaultSecret(token, id);
      if (data.valor) {
        setManualRotate({ id: data.secret.id, valor: data.valor });
      } else {
        setSuccess('Rotação automática aplicada no satélite.');
      }
      const [secs, accs] = await Promise.all([
        fetchVaultSecrets(token, sistema),
        fetchVaultContas(token, sistema),
      ]);
      setSecrets(secs);
      setContas(accs);
    } catch (err) {
      handleVaultError(err);
    }
  }

  async function handleConfirmar(id: number) {
    if (!token) return;
    setErrors([]);
    try {
      await confirmarVaultSecret(token, id);
      setManualRotate(null);
      setManualCreateConta(null);
      setSuccess('Aplicação confirmada. A versão anterior foi revogada.');
      const [secs, accs] = await Promise.all([
        fetchVaultSecrets(token, sistema),
        fetchVaultContas(token, sistema),
      ]);
      setSecrets(secs);
      setContas(accs);
    } catch (err) {
      handleVaultError(err);
    }
  }

  async function handleHistorico(id: number) {
    if (!token) return;
    setErrors([]);
    try {
      const data = await fetchVaultHistorico(token, id);
      setHistorico({ tipo: data.tipo, versoes: data.versoes });
    } catch (err) {
      handleVaultError(err);
    }
  }

  function fillSistemaForm(row: VaultSistema) {
    setSysNome(row.sistema);
    setSysUrl(row.rotation_webhook_url || '');
    setSysSecret('');
    setSysAuto(row.suporta_rotacao_automatica);
    setSistema(row.sistema);
  }

  if (booting) {
    return (
      <div className="py-16 text-center text-sm text-stone-500">
        <Loader2 className="mx-auto size-5 animate-spin" aria-hidden />
      </div>
    );
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-md space-y-5">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <KeyRound className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold tracking-tight text-stone-900">
              Cofre de Credenciais
            </h1>
          </div>
          <p className="text-sm text-stone-500">
            Login próprio do cofre — independente da sessão do Action Hub. A
            ação fica neste serviço e o token dura no máximo 2 horas.
          </p>
        </div>
        <ErrorList messages={errors} />
        <form
          onSubmit={handleLogin}
          className="space-y-3 rounded-2xl border border-stone-200 bg-white p-5"
        >
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              E-mail do cofre
            </span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={fieldClass}
              autoComplete="username"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Senha
            </span>
            <input
              type="password"
              required
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className={fieldClass}
              autoComplete="current-password"
            />
          </label>
          <button
            type="submit"
            disabled={loginBusy}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
          >
            {loginBusy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
            Entrar no cofre
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <KeyRound className="size-5 text-emerald-500" aria-hidden />
            <h1 className="text-xl font-bold tracking-tight text-stone-900 md:text-2xl">
              Cofre de Credenciais
            </h1>
          </div>
          <p className="max-w-xl text-sm text-stone-500">
            Isolado do Action Hub. Revelar e rotacionar ficam no registro de
            auditoria do cofre.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadAll(token, sistema)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <RefreshCw className="size-4" aria-hidden />
            )}
            Atualizar
          </button>
          <button
            type="button"
            onClick={expireSession}
            className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 hover:bg-stone-50"
          >
            <LogOut className="size-4" aria-hidden />
            Sair do cofre
          </button>
        </div>
      </div>

      {success ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {success}
        </div>
      ) : null}
      <ErrorList messages={errors} />

      <form
        onSubmit={handleSaveSistema}
        autoComplete="off"
        className="space-y-3 rounded-2xl border border-stone-200 bg-white p-4"
      >
        <h2 className="text-sm font-bold text-stone-900">Sistemas</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Sistema
            </span>
            <input
              required
              value={sysNome}
              onChange={(e) => setSysNome(e.target.value)}
              className={fieldClass}
              placeholder="phanton"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              URL de rotação
            </span>
            <input
              name={rotationUrlName}
              autoComplete="off"
              value={sysUrl}
              onChange={(e) => setSysUrl(e.target.value)}
              className={fieldClass}
              placeholder="https://…"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
              Segredo do canal S2S
            </span>
            <input
              name={s2sChannelName}
              autoComplete="off"
              type="password"
              value={sysSecret}
              onChange={(e) => setSysSecret(e.target.value)}
              className={fieldClass}
              placeholder="em branco = manter o atual"
            />
          </label>
          <label className="flex items-center gap-2 pt-6 text-sm text-stone-700">
            <input
              type="checkbox"
              checked={sysAuto}
              onChange={(e) => setSysAuto(e.target.checked)}
            />
            Rotação automática
          </label>
        </div>
        <button
          type="submit"
          disabled={sysSaving}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
        >
          {sysSaving ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Plus className="size-4" aria-hidden />}
          Salvar sistema
        </button>
        {sistemas.length ? (
          <div className="flex flex-wrap gap-2 pt-1">
            {sistemas.map((row) => (
              <button
                key={row.sistema}
                type="button"
                onClick={() => fillSistemaForm(row)}
                className={`rounded-lg border px-2.5 py-1 text-xs font-semibold ${
                  sistema === row.sistema
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                    : 'border-stone-200 bg-white text-stone-600'
                }`}
              >
                {row.sistema}
                {row.suporta_rotacao_automatica ? ' · auto' : ''}
              </button>
            ))}
          </div>
        ) : null}
      </form>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-[14rem] flex-1 flex-col gap-1">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
            Sistema selecionado
          </span>
          <select
            value={sistema}
            onChange={(e) => setSistema(e.target.value)}
            className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-800 outline-none ring-emerald-200 focus:ring-2"
          >
            <option value="">Selecione…</option>
            {sistemas.map((row) => (
              <option key={row.sistema} value={row.sistema}>
                {row.sistema}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex gap-2 border-b border-stone-200" role="tablist">
        {(
          [
            ['secrets', 'Secrets de infraestrutura'],
            ['contas', 'Contas privilegiadas'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={painel === id}
            onClick={() => {
              setPainel(id);
              setErrors([]);
            }}
            className={`px-3 py-2 text-sm font-semibold transition ${
              painel === id
                ? 'border-b-2 border-emerald-500 text-emerald-700'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {painel === 'secrets' ? (
      <>
      <section className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4">
        <h2 className="text-sm font-bold text-stone-900">Secrets deste sistema</h2>

        {sistema ? (
          <form
            onSubmit={handleCreateSecret}
            autoComplete="off"
            className="grid gap-3 border-t border-stone-100 pt-4 md:grid-cols-[1fr_1fr_auto]"
          >
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                Tipo
              </span>
              <input
                required
                name={secretTipoName}
                autoComplete="off"
                list={`vault-secret-tipos-${fieldUid}`}
                value={secTipo}
                onChange={(e) => setSecTipo(e.target.value)}
                className={fieldClass}
                placeholder="ex.: db_password"
              />
              <datalist id={`vault-secret-tipos-${fieldUid}`}>
                <option value="db_password" />
                <option value="api_key" />
                <option value="webhook_secret" />
                <option value="admin_password" />
              </datalist>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                Valor
              </span>
              <div className="flex gap-2">
                <input
                  required
                  name={secretValueName}
                  autoComplete="off"
                  type={showSecValor ? 'text' : 'password'}
                  value={secValor}
                  onChange={(e) => setSecValor(e.target.value)}
                  className={`${fieldClass} min-w-0 flex-1`}
                />
                <button
                  type="button"
                  onClick={() => setShowSecValor((v) => !v)}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-2.5 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                  aria-pressed={showSecValor}
                >
                  {showSecValor ? (
                    <EyeOff className="size-3.5" aria-hidden />
                  ) : (
                    <Eye className="size-3.5" aria-hidden />
                  )}
                  {showSecValor ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={secSaving}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
              >
                {secSaving ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Plus className="size-4" aria-hidden />
                )}
                Adicionar secret
              </button>
            </div>
          </form>
        ) : (
          <p className="border-t border-stone-100 pt-4 text-sm text-stone-500">
            Selecione um sistema para criar um secret.
          </p>
        )}
      </section>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Versão</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Valor</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" />
                  </td>
                </tr>
              ) : secrets.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    Nenhum secret neste sistema.
                  </td>
                </tr>
              ) : (
                secrets.map((row) => (
                  <tr key={row.id} className="hover:bg-stone-50/80">
                    <td className="px-4 py-3 font-semibold text-stone-900">{row.tipo}</td>
                    <td className="px-4 py-3 text-stone-600">{row.versao}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${statusClass(row.status)}`}
                      >
                        {statusLabel(row.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-stone-400">••••••••</td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex flex-wrap justify-end gap-1.5">
                        {row.status !== 'revogado' ? (
                          <button
                            type="button"
                            onClick={() => void handleRevelar(row.id)}
                            className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                          >
                            Revelar
                          </button>
                        ) : null}
                        {row.status === 'ativo' ? (
                          <button
                            type="button"
                            onClick={() => void handleRotacionar(row.id)}
                            className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                          >
                            Rotacionar
                          </button>
                        ) : null}
                        {row.status === 'pendente_aplicacao' ? (
                          <button
                            type="button"
                            onClick={() => void handleConfirmar(row.id)}
                            className="rounded-lg bg-emerald-500 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-400"
                          >
                            Confirmar aplicação
                          </button>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => void handleHistorico(row.id)}
                          className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                        >
                          Histórico
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      </>
      ) : (
      <>
      <section className="space-y-4 rounded-2xl border border-stone-200 bg-white p-4">
        <div>
          <h2 className="text-sm font-bold text-stone-900">Contas privilegiadas</h2>
          <p className="mt-1 text-xs text-stone-500">
            Este painel só guarda a senha. Nível e função dessa conta ficam na{' '}
            <a
              href="/dashboard/identidade"
              className="font-semibold text-emerald-700 underline decoration-emerald-300 underline-offset-2 hover:text-emerald-800"
            >
              Gestão de Identidade
            </a>
            , não aqui.
          </p>
        </div>

        {sistema ? (
          <form
            onSubmit={handleCreateConta}
            autoComplete="off"
            className="grid gap-3 border-t border-stone-100 pt-4 md:grid-cols-2"
          >
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                E-mail
              </span>
              <input
                required
                type="email"
                name={contaEmailName}
                autoComplete="off"
                value={contaEmail}
                onChange={(e) => setContaEmail(e.target.value)}
                className={fieldClass}
                placeholder="admin@sistema.local"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                Nível
              </span>
              <select
                required
                value={contaNivel}
                onChange={(e) => setContaNivel(e.target.value as VaultContaNivel)}
                className={fieldClass}
              >
                {(Object.keys(NIVEL_CONTA_LABEL) as VaultContaNivel[]).map((nivel) => (
                  <option key={nivel} value={nivel}>
                    {NIVEL_CONTA_LABEL[nivel]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                Função (opcional)
              </span>
              <input
                name={contaFuncaoName}
                autoComplete="off"
                value={contaFuncao}
                onChange={(e) => setContaFuncao(e.target.value)}
                className={fieldClass}
                placeholder="ex.: homologação"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] font-semibold uppercase tracking-wide text-stone-400">
                Senha (opcional)
              </span>
              <div className="flex gap-2">
                <input
                  name={contaSenhaName}
                  autoComplete="off"
                  type={showContaSenha ? 'text' : 'password'}
                  value={contaSenha}
                  onChange={(e) => setContaSenha(e.target.value)}
                  className={`${fieldClass} min-w-0 flex-1`}
                  placeholder="vazio = o cofre gera uma"
                />
                <button
                  type="button"
                  onClick={() => setShowContaSenha((v) => !v)}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-2.5 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                  aria-pressed={showContaSenha}
                >
                  {showContaSenha ? (
                    <EyeOff className="size-3.5" aria-hidden />
                  ) : (
                    <Eye className="size-3.5" aria-hidden />
                  )}
                  {showContaSenha ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </label>
            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={contaSaving}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400 disabled:opacity-60"
              >
                {contaSaving ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <Plus className="size-4" aria-hidden />
                )}
                Criar conta
              </button>
            </div>
          </form>
        ) : (
          <p className="border-t border-stone-100 pt-4 text-sm text-stone-500">
            Selecione um sistema para criar uma conta privilegiada.
          </p>
        )}
      </section>

      <div className="overflow-hidden rounded-2xl border border-stone-200 bg-stone-50">
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-white text-[11px] font-bold uppercase tracking-wider text-stone-500">
              <tr>
                <th className="px-4 py-3">E-mail</th>
                <th className="px-4 py-3">Versão</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Valor</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    <Loader2 className="mx-auto size-5 animate-spin" />
                  </td>
                </tr>
              ) : !sistema ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    Selecione um sistema para ver as contas.
                  </td>
                </tr>
              ) : contas.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-stone-500">
                    Nenhuma conta privilegiada neste sistema.
                  </td>
                </tr>
              ) : (
                contas.map((row) => (
                  <tr key={row.id} className="hover:bg-stone-50/80">
                    <td className="px-4 py-3 font-semibold text-stone-900">
                      {row.usuario_email || '—'}
                    </td>
                    <td className="px-4 py-3 text-stone-600">{row.versao}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${statusClass(row.status)}`}
                      >
                        {statusLabel(row.status)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-stone-400">••••••••</td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex flex-wrap justify-end gap-1.5">
                        {row.status !== 'revogado' ? (
                          <button
                            type="button"
                            onClick={() => void handleRevelar(row.id)}
                            className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                          >
                            Revelar
                          </button>
                        ) : null}
                        {row.status === 'ativo' ? (
                          <button
                            type="button"
                            onClick={() => void handleRotacionar(row.id)}
                            className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                          >
                            Rotacionar
                          </button>
                        ) : null}
                        {row.status === 'pendente_aplicacao' ? (
                          <button
                            type="button"
                            onClick={() => void handleConfirmar(row.id)}
                            className="rounded-lg bg-emerald-500 px-2.5 py-1 text-xs font-semibold text-white hover:bg-emerald-400"
                          >
                            Confirmar aplicação
                          </button>
                        ) : null}
                        <button
                          type="button"
                          onClick={() => void handleHistorico(row.id)}
                          className="rounded-lg border border-stone-200 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                        >
                          Histórico
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      </>
      )}

      {revealed ? (
        <Modal
          title="Valor revelado"
          onClose={() => setRevealed(null)}
        >
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Esta revelação ficou registrada na auditoria do cofre. Não copie
            para chat nem armazene em arquivo compartilhado.
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-stone-950 px-3 py-2 font-mono text-xs text-emerald-100">
            {revealed.valor}
          </pre>
        </Modal>
      ) : null}

      {manualCreateConta ? (
        <Modal
          title="Conta criada — copie a senha"
          onClose={() => setManualCreateConta(null)}
        >
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Essa conta precisa ser criada manualmente no sistema — copie a senha
            agora, ela não será mostrada de novo.
          </p>
          <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-stone-400">
            {manualCreateConta.email}
          </p>
          <pre className="mt-2 overflow-x-auto rounded-lg bg-stone-950 px-3 py-2 font-mono text-xs text-emerald-100">
            {manualCreateConta.valor}
          </pre>
          <button
            type="button"
            onClick={() => void handleConfirmar(manualCreateConta.id)}
            className="mt-4 inline-flex rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400"
          >
            Confirmar que apliquei manualmente
          </button>
        </Modal>
      ) : null}

      {manualRotate ? (
        <Modal
          title="Rotação manual"
          onClose={() => setManualRotate(null)}
        >
          <p className="text-sm text-stone-600">
            Aplique este valor no sistema externo e depois confirme. A versão
            anterior continua ativa até a confirmação.
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-stone-950 px-3 py-2 font-mono text-xs text-emerald-100">
            {manualRotate.valor}
          </pre>
          <button
            type="button"
            onClick={() => void handleConfirmar(manualRotate.id)}
            className="mt-4 inline-flex rounded-xl bg-emerald-500 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-400"
          >
            Confirmar aplicação
          </button>
        </Modal>
      ) : null}

      {historico ? (
        <Modal
          title={`Histórico · ${historico.tipo}`}
          onClose={() => setHistorico(null)}
        >
          <table className="min-w-full text-left text-sm">
            <thead className="text-[11px] font-bold uppercase text-stone-500">
              <tr>
                <th className="py-2">Versão</th>
                <th className="py-2">Status</th>
                <th className="py-2">Atualizado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {historico.versoes.map((v) => (
                <tr key={v.id}>
                  <td className="py-2">{v.versao}</td>
                  <td className="py-2">{statusLabel(v.status)}</td>
                  <td className="py-2 text-stone-500">
                    {v.atualizado_em
                      ? new Date(v.atualizado_em).toLocaleString('pt-BR')
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Modal>
      ) : null}
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
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
        className="relative z-10 w-full max-w-lg overflow-hidden rounded-t-2xl bg-white shadow-xl sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <h2 className="text-lg font-bold text-stone-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-stone-400 hover:bg-stone-100"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}
