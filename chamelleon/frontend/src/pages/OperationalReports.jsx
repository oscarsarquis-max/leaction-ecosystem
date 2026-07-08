import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getOperationalReportsSummary,
  listOperationalReports,
  listOperationalSites,
} from '../services/operationalApi';
import { getIndustryLabels, getLabelsFromSites } from '../utils/industryLabels';

function statusTone(report) {
  if (report.pending) return 'pending';
  if (report.goal_achieved === true) return 'success';
  if (report.goal_achieved === false) return 'danger';
  return 'neutral';
}

const TONE_STYLES = {
  success: 'border-emerald-300 bg-emerald-50',
  danger: 'border-red-300 bg-red-50',
  pending: 'border-slate-200 bg-slate-50',
  neutral: 'border-amber-200 bg-amber-50',
};

const TONE_DOT = {
  success: 'bg-emerald-500',
  danger: 'bg-red-500',
  pending: 'bg-slate-400',
  neutral: 'bg-amber-400',
};

function ImpedimentsModal({ report, onClose }) {
  if (!report) return null;
  const labels = getIndustryLabels(report.industry_type);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="impediments-title"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="impediments-title" className="text-lg font-semibold text-slate-900">
              Impeditivos — {labels.unit} {report.site_name}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              {report.report_date || report.date}
              {report.sprint_daily_goal ? ` · Meta: ${report.sprint_daily_goal}` : ''}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-2 py-1 text-sm text-slate-600 hover:bg-slate-50"
            onClick={onClose}
          >
            Fechar
          </button>
        </div>
        <div className="mt-5 space-y-4 text-sm text-slate-700">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Impeditivo</p>
            <p className="mt-1 whitespace-pre-wrap">{report.impediment_details || '—'}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Mitigação</p>
            <p className="mt-1 whitespace-pre-wrap">{report.mitigation_action || '—'}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Prevenção</p>
            <p className="mt-1 whitespace-pre-wrap">{report.preventive_action || '—'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportCard({ report, onOpenImpediments }) {
  const tone = statusTone(report);
  const labels = getIndustryLabels(report.industry_type);

  return (
    <article className={`rounded-xl border-2 p-4 shadow-sm ${TONE_STYLES[tone]}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className={`mt-1.5 h-3 w-3 shrink-0 rounded-full ${TONE_DOT[tone]}`} />
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              {labels.unit}
            </p>
            <h3 className="font-semibold text-slate-900">{report.site_name}</h3>
            {report.site_location && (
              <p className="text-xs text-slate-600">{report.site_location}</p>
            )}
            <p className="mt-2 text-sm text-slate-700">
              {report.pending && `Sem RDO assinado neste(a) ${labels.unit.toLowerCase()}.`}
              {!report.pending && report.goal_achieved === true && 'Meta atingida no Gemba.'}
              {!report.pending && report.goal_achieved === false && 'Meta não atingida.'}
              {!report.pending && report.goal_achieved == null && 'Daily sem resposta de meta.'}
            </p>
            {report.sprint_daily_goal && (
              <p className="mt-2 text-xs text-slate-600">
                <span className="font-medium">🎯 Meta:</span> {report.sprint_daily_goal}
              </p>
            )}
          </div>
        </div>
        {report.goal_achieved === false && (
          <button
            type="button"
            className="shrink-0 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
            onClick={() => onOpenImpediments(report)}
          >
            Ver Impeditivos
          </button>
        )}
      </div>
    </article>
  );
}

function DailyFarolTab({ reportDate, setReportDate, reports, loading, error, onSelect }) {
  const listLabels = useMemo(
    () => getLabelsFromSites(reports.map((r) => ({ industry_type: r.industry_type }))),
    [reports],
  );

  const stats = {
    success: reports.filter((r) => r.goal_achieved === true).length,
    danger: reports.filter((r) => r.goal_achieved === false).length,
    pending: reports.filter((r) => r.pending).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="text-sm text-slate-600">
          Farol consolidado dos {listLabels.unitPlural.toLowerCase()} no dia selecionado.
        </p>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Data</span>
          <input
            type="date"
            className="mt-1 rounded-lg border border-slate-300 px-3 py-2"
            value={reportDate}
            onChange={(e) => setReportDate(e.target.value)}
          />
        </label>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3 font-semibold">{listLabels.nameColumn}</th>
              <th className="px-4 py-3 font-semibold">Setor</th>
              <th className="px-4 py-3 font-semibold">Farol</th>
              <th className="px-4 py-3 font-semibold text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {!loading && reports.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-slate-500">
                  Nenhum(a) {listLabels.unit.toLowerCase()} cadastrado(a).
                </td>
              </tr>
            )}
            {reports.map((report) => {
              const labels = getIndustryLabels(report.industry_type);
              const tone = statusTone(report);
              const farolLabel =
                tone === 'success'
                  ? 'Meta batida'
                  : tone === 'danger'
                    ? 'Meta perdida'
                    : tone === 'pending'
                      ? 'Sem relatório'
                      : 'Sem resposta';
              return (
                <tr
                  key={
                    report.id ||
                    `${report.operational_site_id || report.site_id}-${report.report_date}`
                  }
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{report.site_name}</p>
                    <p className="text-xs text-slate-500">{labels.unit}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">{report.industry_type || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center gap-2 text-sm text-slate-700">
                      <span className={`h-2.5 w-2.5 rounded-full ${TONE_DOT[tone]}`} />
                      {farolLabel}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {report.goal_achieved === false ? (
                      <button
                        type="button"
                        className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
                        onClick={() => onSelect(report)}
                      >
                        Ver Impeditivos
                      </button>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
          <p className="text-2xl font-bold text-emerald-700">{stats.success}</p>
          <p className="text-xs font-medium text-emerald-800">Metas batidas</p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center">
          <p className="text-2xl font-bold text-red-700">{stats.danger}</p>
          <p className="text-xs font-medium text-red-800">Metas perdidas</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-center">
          <p className="text-2xl font-bold text-slate-600">{stats.pending}</p>
          <p className="text-xs font-medium text-slate-700">Sem relatório</p>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-500">Carregando farol…</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {reports.map((report) => (
            <ReportCard
              key={`card-${report.id || report.operational_site_id || report.site_id}-${report.report_date}`}
              report={report}
              onOpenImpediments={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ConsolidatedTab({
  startDate,
  endDate,
  siteId,
  sites,
  summary,
  loading,
  error,
  onStartDate,
  onEndDate,
  onSiteId,
  onReload,
  onSelect,
}) {
  const listLabels = useMemo(() => getLabelsFromSites(sites), [sites]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end gap-4">
        <label className="block text-sm">
          <span className="font-medium text-slate-700">De</span>
          <input
            type="date"
            className="mt-1 block rounded-lg border border-slate-300 px-3 py-2"
            value={startDate}
            onChange={(e) => onStartDate(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-slate-700">Até</span>
          <input
            type="date"
            className="mt-1 block rounded-lg border border-slate-300 px-3 py-2"
            value={endDate}
            onChange={(e) => onEndDate(e.target.value)}
          />
        </label>
        <label className="block min-w-[200px] flex-1 text-sm">
          <span className="font-medium text-slate-700">{listLabels.unit}</span>
          <select
            className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
            value={siteId}
            onChange={(e) => onSiteId(e.target.value)}
          >
            <option value="">Todos os {listLabels.unitPlural.toLowerCase()}</option>
            {sites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          onClick={onReload}
        >
          Atualizar
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">Carregando consolidado…</p>}

      {!loading && summary && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
              <p className="text-2xl font-bold text-slate-900">{summary.total_days_planned ?? 0}</p>
              <p className="text-xs font-medium text-slate-600">Dias planejados / reportados</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
              <p className="text-2xl font-bold text-emerald-700">
                {summary.total_goals_achieved ?? 0}
              </p>
              <p className="text-xs font-medium text-emerald-800">Metas atingidas</p>
            </div>
            <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-center">
              <p className="text-2xl font-bold text-indigo-700">{summary.success_rate ?? 0}%</p>
              <p className="text-xs font-medium text-indigo-800">Taxa de sucesso</p>
            </div>
          </div>

          <section>
            <h2 className="text-base font-semibold text-slate-900">Impeditivos consolidados</h2>
            <p className="mt-1 text-sm text-slate-600">
              Dias em que a meta não foi atingida no período selecionado.
            </p>

            <div className="mt-4 space-y-3">
              {(summary.consolidated_impediments || []).length === 0 && (
                <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
                  Nenhum impeditivo no período.
                </div>
              )}
              {(summary.consolidated_impediments || []).map((item) => {
                const labels = getIndustryLabels(item.industry_type);
                return (
                  <article
                    key={item.id}
                    className="rounded-xl border border-red-200 bg-red-50/40 p-4 shadow-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                          {labels.unit} · {item.date}
                        </p>
                        <h3 className="font-semibold text-slate-900">{item.site_name}</h3>
                        {item.sprint_daily_goal && (
                          <p className="mt-1 text-xs text-slate-600">
                            Meta: {item.sprint_daily_goal}
                          </p>
                        )}
                      </div>
                      <button
                        type="button"
                        className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
                        onClick={() => onSelect(item)}
                      >
                        Ver detalhes
                      </button>
                    </div>
                    <p className="mt-3 line-clamp-2 text-sm text-slate-700">
                      {item.impediment_details || 'Sem detalhes registrados.'}
                    </p>
                  </article>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function defaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 6);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export default function OperationalReports() {
  const [activeTab, setActiveTab] = useState('daily');
  const [reportDate, setReportDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [reports, setReports] = useState([]);
  const [dailyLoading, setDailyLoading] = useState(true);
  const [dailyError, setDailyError] = useState('');
  const [selected, setSelected] = useState(null);

  const range = useMemo(() => defaultRange(), []);
  const [startDate, setStartDate] = useState(range.start);
  const [endDate, setEndDate] = useState(range.end);
  const [siteId, setSiteId] = useState('');
  const [sites, setSites] = useState([]);
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState('');

  const loadDaily = useCallback(async () => {
    setDailyLoading(true);
    setDailyError('');
    try {
      const data = await listOperationalReports(reportDate);
      setReports(data.reports || []);
    } catch (err) {
      setDailyError(err.message || 'Erro ao carregar farol operacional.');
      setReports([]);
    } finally {
      setDailyLoading(false);
    }
  }, [reportDate]);

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError('');
    try {
      const data = await getOperationalReportsSummary({
        startDate,
        endDate,
        siteId: siteId || undefined,
      });
      setSummary(data);
    } catch (err) {
      setSummaryError(err.message || 'Erro ao carregar relatório consolidado.');
      setSummary(null);
    } finally {
      setSummaryLoading(false);
    }
  }, [startDate, endDate, siteId]);

  useEffect(() => {
    loadDaily();
  }, [loadDaily]);

  useEffect(() => {
    listOperationalSites()
      .then((data) => setSites(data.sites || []))
      .catch(() => setSites([]));
  }, []);

  useEffect(() => {
    if (activeTab === 'consolidated') {
      loadSummary();
    }
  }, [activeTab, loadSummary]);

  const tabs = [
    { id: 'daily', label: 'Visão Diária (Farol)' },
    { id: 'consolidated', label: 'Relatório Consolidado' },
  ];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">Relatórios Operacionais</h1>
        <p className="mt-1 text-sm text-slate-600">
          Acompanhe o farol do dia e o desempenho consolidado da Área Operacional.
        </p>
      </header>

      <div className="flex gap-1 border-b border-slate-200" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`px-4 py-2.5 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'border-b-2 border-slate-900 text-slate-900'
                : 'text-slate-500 hover:text-slate-800'
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'daily' && (
        <DailyFarolTab
          reportDate={reportDate}
          setReportDate={setReportDate}
          reports={reports}
          loading={dailyLoading}
          error={dailyError}
          onSelect={setSelected}
        />
      )}

      {activeTab === 'consolidated' && (
        <ConsolidatedTab
          startDate={startDate}
          endDate={endDate}
          siteId={siteId}
          sites={sites}
          summary={summary}
          loading={summaryLoading}
          error={summaryError}
          onStartDate={setStartDate}
          onEndDate={setEndDate}
          onSiteId={setSiteId}
          onReload={loadSummary}
          onSelect={setSelected}
        />
      )}

      <ImpedimentsModal report={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
