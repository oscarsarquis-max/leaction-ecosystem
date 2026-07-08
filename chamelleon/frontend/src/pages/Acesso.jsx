import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { checkEmail, login, resendAccessCode } from '../services/api';
import { applyPostLoginRedirect, loginDataFromSession } from '../utils/appLauncher';
import { clearSession, getSession } from '../services/session';

export default function Acesso() {
  const navigate = useNavigate();
  const { accessCode: accessCodeFromUrl } = useParams();
  const { loginWithResponse, isAuthenticated, logout } = useAuth();
  const [email, setEmail] = useState('');
  const [credential, setCredential] = useState('');
  const [userType, setUserType] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // Só na abertura da tela — evita corrida com handleLogin após novo login
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('logout') === '1') {
      logout();
      clearSession();
      window.history.replaceState({}, '', '/acesso');
      return;
    }

    if (!isAuthenticated) return;
    const payload = loginDataFromSession(getSession());
    if (!payload) return;
    applyPostLoginRedirect(payload, navigate);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (accessCodeFromUrl) {
      setCredential(accessCodeFromUrl.trim());
    }
  }, [accessCodeFromUrl]);

  async function resolveEmailType() {
    const trimmed = email.trim();
    if (!trimmed) {
      setUserType(null);
      setMessage('');
      return;
    }
    try {
      const data = await checkEmail(trimmed);
      setUserType(data.type);
      setMessage(data.message || '');
      if (data.type === 'LEAD' && data.dev_access_code) {
        setCredential(data.dev_access_code);
        setMessage(
          `${data.message || ''} Código atual (dev): ${data.dev_access_code}`.trim()
        );
      }
      if (data.type === 'UNKNOWN') {
        setError(data.message);
      } else {
        setError('');
      }
    } catch (err) {
      setUserType(null);
      setMessage('');
      setError(err.message || 'Erro ao verificar e-mail.');
    }
  }

  async function handleResendCode() {
    const trimmed = email.trim();
    if (!trimmed) {
      setError('Digite seu e-mail.');
      return;
    }
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const data = await resendAccessCode(trimmed);
      setUserType('LEAD');
      if (data.dev_access_code) {
        setCredential(data.dev_access_code);
      }
      setMessage(
        data.dev_access_code
          ? `${data.message} Código (dev): ${data.dev_access_code}`
          : data.message || 'Novo código enviado.'
      );
    } catch (err) {
      setError(err.message || 'Não foi possível reenviar o código.');
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(e) {
    e?.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedCredential = credential.trim();

    if (!trimmedEmail) {
      setError('Digite seu e-mail.');
      return;
    }
    if (!trimmedCredential) {
      setError(userType === 'TEAM' ? 'Digite sua senha.' : 'Digite o código LA-*.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      const data = await login(trimmedEmail, trimmedCredential);
      if (!data.success) {
        setError(data.error || 'Credenciais inválidas.');
        return;
      }

      // Persiste sessão e redireciona — executor sai antes do re-render do React
      loginWithResponse(data);
      const dest = applyPostLoginRedirect(data, navigate);
      if (dest === 'external') return;
    } catch (err) {
      const msg = err.message || 'Credenciais inválidas.';
      if (err.status === 401 || msg.toLowerCase().includes('código')) {
        setError(
          'Código inválido ou desatualizado. Clique em "Reenviar código" para gerar um novo LA-*.'
        );
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  const credentialLabel =
    userType === 'TEAM' ? 'Senha de equipe' : 'Código de acesso (LA-*)';

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-chameleon/10 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <div className="mb-6 text-center">
          <img
            src="/images/camelleonlogo.png"
            alt="Chamelleon"
            className="mx-auto mb-3 h-16 w-16 rounded-xl object-cover"
          />
          <h1 className="text-2xl font-bold text-slate-800">Bem-vindo</h1>
          <p className="mt-1 text-sm text-slate-500">
            Informe e-mail e código LA-* (ou senha de equipe).
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">E-mail</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={resolveEmailType}
              placeholder="nome@empresa.com"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-chameleon focus:outline-none focus:ring-2 focus:ring-chameleon/20"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700">{credentialLabel}</span>
            <input
              type={userType === 'TEAM' ? 'password' : 'text'}
              required
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              placeholder={userType === 'TEAM' ? '••••••••' : 'Ex: LA-ABC123'}
              autoComplete={userType === 'TEAM' ? 'current-password' : 'one-time-code'}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm font-mono tracking-wide focus:border-chameleon focus:outline-none focus:ring-2 focus:ring-chameleon/20"
            />
          </label>

          {accessCodeFromUrl && (
            <p className="text-xs text-amber-700">
              Link do e-mail detectado. Se o login falhar, o código já foi substituído — use
              &quot;Reenviar código&quot;.
            </p>
          )}

          {message && !error && (
            <p className="text-xs text-slate-500">{message}</p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-chameleon py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
          >
            {busy ? 'Entrando...' : 'Entrar'}
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={handleResendCode}
            className="w-full text-center text-xs font-medium text-chameleon hover:underline disabled:opacity-60"
          >
            Não recebeu o e-mail? Reenviar código LA-*
          </button>
        </form>

        {error && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          Primeiro acesso?{' '}
          <Link to="/cadastro" className="font-medium text-chameleon hover:underline">
            Solicitar cadastro e código
          </Link>
        </p>
      </div>
    </div>
  );
}
