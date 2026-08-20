import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  getWeeklyGoals,
  listOperationalSites,
  pushWeeklyGoals,
  syncOperationalSiteSatellite,
} from '../services/operationalApi';
import { getIndustryLabels, getLabelsFromSites, selectUnitPrompt } from '../utils/industryLabels';

const WEEKDAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

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

/** Um input vazio por dia da semana — permite limpar dia no replace. */
function emptyCommitmentsForWeek(dates) {
  return Object.fromEntries((dates || []).map((d) => [d, ['']]));
}

function descriptionsFromApi(dayItems) {
  if (!Array.isArray(dayItems) || !dayItems.length) return [''];
  const texts = dayItems
    .map((item) => (typeof item === 'string' ? item : item?.description || ''))
    .map((t) => String(t));
  return texts.length ? texts : [''];
}

export default function OperationalPlanning() {
  const [sites, setSites] = useState([]);
  const [siteId, setSiteId] = useState('');
  const [weekDates, setWeekDates] = useState(() => weekIsoDates());
  const [commitments, setCommitments] = useState(() =>
    emptyCommitmentsForWeek(weekIsoDates()),
  );
  const [referenceDate, setReferenceDate] = useState(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [loading, setLoading] = useState(true);
  const [loadingGoals, setLoadingGoals] = useState(false);
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
      setSiteId((prev) => prev || (list[0]?.id ?? ''));
    } catch (err) {
      setError(err.message || 'Erro ao carregar unidades.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadCommitmentsForWeek = useCallback(async (currentSiteId, dates) => {
    if (!currentSiteId || !dates?.length) {
      setCommitments(emptyCommitmentsForWeek(dates));
      return;
    }
    setLoadingGoals(true);
    try {
      const res = await getWeeklyGoals({
        siteId: currentSiteId,
        startDate: dates[0],
        endDate: dates[dates.length - 1],
      });
      const saved = res.commitments || {};
      const next = emptyCommitmentsForWeek(dates);
      dates.forEach((d) => {
        next[d] = descriptionsFromApi(saved[d]);
      });
      setCommitments(next);
    } catch (err) {
      setCommitments(emptyCommitmentsForWeek(dates));
      setError(err.message || 'Não foi possível carregar compromissos salvos.');
    } finally {
      setLoadingGoals(false);
    }
  }, []);

  useEffect(() => {
    loadSites();
  }, [loadSites]);

  useEffect(() => {
    const dates = weekIsoDates(referenceDate);
    setWeekDates(dates);
    if (siteId) {
      void loadCommitmentsForWeek(siteId, dates);
    } else {
      setCommitments(emptyCommitmentsForWeek(dates));
    }
  }, [referenceDate, siteId, loadCommitmentsForWeek]);

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

  function updateDayItem(iso, index, value) {
    setCommitments((prev) => {
      const list = [...(prev[iso] || [''])];
      list[index] = value;
      return { ...prev, [iso]: list };
    });
  }

  function addDayItem(iso) {
    setCommitments((prev) => {
      const list = [...(prev[iso] || [''])];
      list.push('');
      return { ...prev, [iso]: list };
    });
  }

  function removeDayItem(iso, index) {
    setCommitments((prev) => {
      const list = [...(prev[iso] || [''])];
      list.splice(index, 1);
      return { ...prev, [iso]: list.length ? list : [''] };
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!siteId) {
      setError(selectUnitPrompt(null));
      return;
    }

    // Envia todos os dias da semana (items [] limpa o dia no backend).
    const payloadCommitments = weekDates.map((date) => ({
      date,
      items: (commitments[date] || [])
        .map((t) => String(t || '').trim())
        .filter(Boolean),
    }));

    const nonEmptyCount = payloadCommitments.reduce(
      (acc, day) => acc + day.items.length,
      0,
    );
    if (!nonEmptyCount) {
      // Ainda envia (limpa a semana) — usuário pode ter apagado tudo de propósito.
    }

    setSaving(true);
    setError('');
    setMessage('');
    try {
      const data = await pushWeeklyGoals({
        site_id: siteId,
        commitments: payloadCommitments,
      });
      const savedMap = data.commitments || {};
      setCommitments((prev) => {
        const next = { ...prev };
        weekDates.forEach((day) => {
          next[day] = descriptionsFromApi(savedMap[day]);
        });
        return next;
      });
      const localCount = data.saved_count ?? nonEmptyCount;
      if (data.satellite_warning) {
        setMessage(`${localCount} compromisso(s) salvos. ${data.satellite_warning}`);
      } else {
        const sat = data?.satellite?.total || localCount;
        setMessage(
          `Plano persistido (${localCount} compromisso(s) locais; ${sat} no Diário).`,
        );
      }
      if (data.site) {
        setSites((prev) =>
          prev.map((s) => (s.id === data.site.id ? { ...s, ...data.site } : s)),
        );
      }
    } catch (err) {
      setError(err.message || 'Erro ao salvar o planejamento semanal.');
    } finally {
      setSaving(false);
    }
  }

  async function handleSyncSatellite() {
    if (!siteId) {
      setError(selectUnitPrompt(null));
      return;
    }
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const res = await syncOperationalSiteSatellite(siteId);
      setMessage(res.site?.message || 'Canteiro sincronizado com o Diário de Obra.');
      await loadSites();
    } catch (err) {
      setError(
        err.message ||
          'Falha ao sincronizar. Suba o Diário de Obra (apps\\start-diario-obra.ps1) e tente de novo.',
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
          Defina os compromissos diários (Last Planner) por {labels.unit.toLowerCase()}.
          Os compromissos são salvos no Chamelleon e publicados no Diário de Obra
          quando o canteiro estiver sincronizado.
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
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p>
                Este(a) {labels.unit.toLowerCase()} ainda não está vinculado(a) ao
                Diário de Obra. Você já pode salvar compromissos no Chamelleon; para
                publicar no Diário, sincronize:
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={saving}
                  onClick={handleSyncSatellite}
                  className="rounded-lg bg-amber-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-900 disabled:opacity-60"
                >
                  Sincronizar com Diário
                </button>
                <Link
                  to="/operational/sites"
                  className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-900 hover:bg-amber-100"
                >
                  Ir para Gestão de Unidades
                </Link>
              </div>
            </div>
          )}

          {loadingGoals && (
            <p className="text-xs text-slate-500">
              Carregando compromissos salvos da semana…
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {weekDates.map((iso, index) => {
              const items = commitments[iso] || [''];
              return (
                <div
                  key={iso}
                  className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {WEEKDAY_LABELS[index] || `D${index + 1}`} · {formatDisplayDate(iso)}
                  </span>
                  <ul className="mt-2 space-y-2">
                    {items.map((text, itemIndex) => (
                      <li key={`${iso}-${itemIndex}`} className="flex gap-1">
                        <input
                          type="text"
                          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                          placeholder={`Compromisso ${itemIndex + 1}…`}
                          value={text}
                          onChange={(e) =>
                            updateDayItem(iso, itemIndex, e.target.value)
                          }
                        />
                        <button
                          type="button"
                          title="Remover compromisso"
                          className="rounded-lg border border-slate-200 px-2 text-sm text-slate-500 hover:bg-slate-50"
                          onClick={() => removeDayItem(iso, itemIndex)}
                          disabled={items.length <= 1 && !String(text || '').trim()}
                        >
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="mt-2 text-xs font-semibold text-chameleon hover:underline"
                    onClick={() => addDayItem(iso)}
                  >
                    + Adicionar compromisso
                  </button>
                </div>
              );
            })}
          </div>

          <button
            type="submit"
            disabled={saving || !siteId || loadingGoals}
            className="rounded-lg bg-chameleon px-5 py-2.5 text-sm font-semibold text-white hover:bg-chameleon-dark disabled:opacity-60"
          >
            {saving ? 'Salvando plano…' : 'Salvar Plano'}
          </button>
        </form>
      )}
    </div>
  );
}
