import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { listSectors, registerLead } from '../services/api';

export default function Cadastro() {
  const navigate = useNavigate();
  const [sectors, setSectors] = useState([]);
  const [sectorState, setSectorState] = useState('loading');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [form, setForm] = useState({
    name: '',
    email: '',
    company_name: '',
    framework_id: '',
    document: '',
  });

  const loadSectors = useCallback(async () => {
    setSectorState('loading');
    setError('');
    try {
      const data = await listSectors();
      const items = data.sectors || [];
      setSectors(items);
      if (items.length === 0) {
        setSectorState('empty');
        return;
      }
      setSectorState('ready');
      const defaultSector =
        items.find((s) => s.framework_id === 'educacao-v1') || items[0];
      if (defaultSector) {
        setForm((f) => ({ ...f, framework_id: defaultSector.framework_id }));
      }
    } catch (err) {
      setSectors([]);
      setSectorState('error');
      setError(err.message || 'Não foi possível carregar os setores disponíveis.');
    }
  }, []);

  useEffect(() => {
    loadSectors();
  }, [loadSectors]);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.framework_id) {
      setError('Selecione o setor de atuação antes de continuar.');
      return;
    }
    setBusy(true);
    setError('');
    setSuccess('');
    try {
      const result = await registerLead(form);
      const devCode = result.dev_access_code
        ? ` Código para teste: ${result.dev_access_code}`
        : '';
      setSuccess((result.message || 'Cadastro realizado! Verifique seu e-mail.') + devCode);
      setTimeout(() => navigate('/acesso'), devCode ? 5000 : 2500);
    } catch (err) {
      const msg = err.message || 'Erro ao cadastrar.';
      if (msg.includes('CNPJ') || msg.includes('documento')) {
        setError(`${msg} Dica: deixe o CNPJ em branco para tentar novamente.`);
      } else if (msg.includes('outro perfil')) {
        setError(`${msg} Utilize a tela de login com senha de equipe.`);
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }

  const canSubmit = sectorState === 'ready' && sectors.length > 0;

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-chameleon/10 px-4 py-10">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <div className="mb-6">
          <Link to="/acesso" className="text-sm font-medium text-chameleon hover:underline">
            ← Voltar ao login
          </Link>
          <h1 className="mt-3 text-2xl font-bold text-slate-800">Solicitar Diagnóstico</h1>
          <p className="mt-1 text-sm text-slate-500">
            Informe seus dados e o setor de atuação. Enviaremos um código LA-* para o e-mail
            cadastrado.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-sm">
            <span className="font-medium text-slate-700">Nome completo *</span>
            <input
              required
              value={form.name}
              onChange={(e) => updateField('name', e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700">E-mail *</span>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700">Empresa / Organização *</span>
            <input
              required
              value={form.company_name}
              onChange={(e) => updateField('company_name', e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700">CNPJ / Documento (opcional)</span>
            <input
              value={form.document}
              onChange={(e) => updateField('document', e.target.value)}
              placeholder="Opcional — deixe em branco se já tentou antes"
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium text-slate-700">Setor de atuação *</span>
            {sectorState === 'loading' ? (
              <p className="mt-2 text-xs text-slate-500">Carregando setores disponíveis...</p>
            ) : sectorState === 'error' ? (
              <div className="mt-2 space-y-2">
                <p className="text-xs text-red-600">
                  {error || 'Não foi possível carregar os setores disponíveis.'}
                </p>
                <button
                  type="button"
                  onClick={loadSectors}
                  className="text-xs font-medium text-chameleon hover:underline"
                >
                  Tentar novamente
                </button>
              </div>
            ) : sectorState === 'empty' ? (
              <p className="mt-2 text-xs text-amber-700">
                Nenhum setor publicado no momento. Peça ao administrador para publicar um
                setor no Builder.
              </p>
            ) : (
              <select
                required
                value={form.framework_id}
                onChange={(e) => updateField('framework_id', e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"
              >
                <option value="">Selecione o setor...</option>
                {sectors.map((sector) => (
                  <option key={sector.framework_id} value={sector.framework_id}>
                    {sector.label}
                  </option>
                ))}
              </select>
            )}
          </label>

          <button
            type="submit"
            disabled={busy || !canSubmit}
            className="w-full rounded-lg bg-chameleon py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
          >
            {busy ? 'Enviando...' : 'Receber código de acesso'}
          </button>
        </form>

        {error && sectorState !== 'error' && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        {success && (
          <p className="mt-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">
            {success}
          </p>
        )}
      </div>
    </div>
  );
}
