import { useCallback, useEffect, useMemo, useState } from 'react';
import { getSession } from '../services/session';
import { listOperationalSites } from '../services/operationalApi';
import { getIndustryLabels, getLabelsFromSites, selectUnitPrompt } from '../utils/industryLabels';

const WEEKDAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

const DIARIO_API_URL = (
  import.meta.env.VITE_DIARIO_OBRA_API_URL || 'http://localhost:6010'
).replace(/\/$/, '');

const INTEGRATION_API_KEY = import.meta.env.VITE_INTEGRATION_API_KEY || '';

function mondayOfWeek(isoDate) {
  const d = new Date(`${isoDate}T12:00:00`);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

function weekIsoDates(referenceIso) {
  const monday = mondayOfWeek(referenceIso || new Date().toISOString().slice(0, 10));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

function formatDisplayDate(iso) {
  const d = new Date(`${iso}T12:00:00`);
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

export default function OperationalPlanning() {
  const [sites, setSites] = useState([]);
  const [siteId, setSiteId] = useState('');
  const [weekDates, setWeekDates] = useState(() => weekIsoDates());
  const [goals, setGoals] = useState({});
  const [referenceDate, setReferenceDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const loadSites = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listOperationalSites();
      const list = data.sites || [];
      setSites(list);
      if (!siteId && list.length) setSiteId(list[0].id);
    } catch (err) {
      setError(err.message || 'Erro ao carregar unidades.');
    } finally {
      setLoading(false);
    }
  }, [siteId]);

  useEffect(() => {
    loadSites();
  }, []);

  useEffect(() => {
    const dates = weekIsoDates(referenceDate);
    setWeekDates(dates);
    setGoals((prev) => {
      const next = { ...prev };
      dates.forEach((d) => {
        if (next[d] === undefined) next[d] = '';
      });
      return next;
    });
  }, [referenceDate]);

  const selectedSite = useMemo(() => sites.find((s) => s.id === siteId), [sites, siteId]);
  const labels = useMemo(
    () =>
      selectedSite
        ? getIndustryLabels(selectedSite.industry_type)
        : getLabelsFromSites(sites),
    [selectedSite, sites],
  );

  function shiftWeek(delta) {
    const base = new Date(`${referenceDate}T12:00:00`);
    base.setDate(base.getDate() + delta * 7);
    setReferenceDate(base.toISOString().slice(0, 10));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!siteId) {
      setError(selectUnitPrompt(null));
      return;
    }
    if (!selectedSite?.satellite_site_id) {
      setError(
        `${labels.unit} sem vínculo com o Diário de Obra. Sincronize um canteiro de Construção em Configurações da Organização.`,
      );
      return;
    }

    const payloadGoals = weekDates
      .map((date) => ({ date, sprint_daily_goal: (goals[date] || '').trim() }))
      .filter((g) => g.sprint_daily_goal);

    if (!payloadGoals.length) {
      setError('Informe ao menos uma meta diária.');
      return;
    }

    const session = getSession();
    const tenantId = selectedSite.tenant_id || session?.tenantId;
    if (!tenantId) {
      setError('Sessão sem tenant_id.');
      return;
    }

    setSaving(true);
    setError('');
    setMessage('');
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (INTEGRATION_API_KEY) headers['X-Integration-Key'] = INTEGRATION_API_KEY;

      const response = await fetch(`${DIARIO_API_URL}/api/integration/daily-goals`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          tenant_id: tenantId,
          project_id: selectedSite.satellite_site_id,
          goals: payloadGoals,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `Satélite respondeu HTTP ${response.status}`);
      }
      setMessage(
        `Plano salvo no Diário de Obra (${data.total || payloadGoals.length} meta(s) injetadas).`,
      );
    } catch (err) {
      setError(
        err.message ||
          'Erro ao salvar plano no satélite. Confirme se o Diário de Obra está em :6010.',
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Planejamento Semanal</h1>
        <p className="mt-1 text-sm text-slate-600">
          Defina as metas diárias (Sprint Goals) por {labels.unit.toLowerCase()} e publique no Diário
          de Obra.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {message}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block text-sm">
          <span className="font-medium text-slate-700">
            {selectUnitPrompt(selectedSite?.industry_type)}
          </span>
          <select
            className="mt-1 min-w-[220px] rounded-lg border border-slate-300 px-3 py-2"
            value={siteId}
            onChange={(e) => setSiteId(e.target.value)}
          >
            <option value="">{selectUnitPrompt(null)}</option>
            {sites.map((site) => {
              const siteLabels = getIndustryLabels(site.industry_type);
              return (
                <option key={site.id} value={site.id}>
                  {site.name} · {siteLabels.unit}
                </option>
              );
            })}
          </select>
        </label>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            onClick={() => shiftWeek(-1)}
          >
            ← Semana anterior
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            onClick={() => shiftWeek(1)}
          >
            Próxima semana →
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {selectedSite && !selectedSite.satellite_site_id && (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Este(a) {labels.unit.toLowerCase()} ainda não está vinculado(a) ao satélite. Sincronize
              em Configurações da Organização (indústria Construção).
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {weekDates.map((iso, index) => (
              <label key={iso} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {WEEKDAY_LABELS[index]} · {formatDisplayDate(iso)}
                </span>
                <textarea
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  rows={3}
                  placeholder="Meta do dia (Sprint Goal)…"
                  value={goals[iso] || ''}
                  onChange={(e) => setGoals({ ...goals, [iso]: e.target.value })}
                />
              </label>
            ))}
          </div>

          <button
            type="submit"
            disabled={saving || !siteId}
            className="rounded-lg bg-chameleon px-5 py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
          >
            {saving ? 'Salvando plano…' : 'Salvar Plano'}
          </button>
        </form>
      )}
    </div>
  );
}
