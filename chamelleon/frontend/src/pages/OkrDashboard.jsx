import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  createOkrDriver,
  createOkrKeyResult,
  createOkrKpi,
  createOkrObjective,
  fetchOkrDashboard,
  updateOkrKeyResult,
  updateOkrKpi,
} from '../services/okrApi';

function formatMetric(value, unit) {
  const num = Number(value);
  const formatted = Number.isFinite(num)
    ? num.toLocaleString('pt-BR', { maximumFractionDigits: 2 })
    : '—';
  return unit ? `${formatted} ${unit}` : formatted;
}

function ProgressBar({ pct, tone = 'green' }) {
  const width = Math.min(100, Math.max(0, Number(pct) || 0));
  const bar =
    tone === 'gold'
      ? 'bg-gradient-to-r from-amber-500 to-yellow-400'
      : 'bg-chameleon';
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full transition-all ${bar}`} style={{ width: `${width}%` }} />
    </div>
  );
}

function ValueEditor({ label, current, target, unit, saving, onSave }) {
  const [draft, setDraft] = useState(String(current ?? 0));
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setDraft(String(current ?? 0));
  }, [current]);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-chameleon/40 hover:text-chameleon-dark"
      >
        Atualizar {label}
      </button>
    );
  }

  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={async (e) => {
        e.preventDefault();
        const value = Number(String(draft).replace(',', '.'));
        if (!Number.isFinite(value)) return;
        await onSave(value);
        setOpen(false);
      }}
    >
      <label className="text-[11px] font-semibold text-slate-500">
        Valor atual {unit ? `(${unit})` : ''}
        <input
          type="number"
          step="any"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className="mt-0.5 block w-28 rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
          autoFocus
        />
      </label>
      <p className="pb-1.5 text-[11px] text-slate-400">Alvo: {formatMetric(target, unit)}</p>
      <button
        type="submit"
        disabled={saving}
        className="rounded-lg bg-chameleon px-3 py-1.5 text-xs font-bold text-white hover:bg-chameleon-dark disabled:opacity-50"
      >
        {saving ? 'Salvando…' : 'Salvar'}
      </button>
      <button
        type="button"
        onClick={() => {
          setDraft(String(current ?? 0));
          setOpen(false);
        }}
        className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-50"
      >
        Cancelar
      </button>
    </form>
  );
}

const CREATE_MODES = [
  { id: 'driver', label: 'Direcionador' },
  { id: 'objective', label: 'Objetivo' },
  { id: 'kr', label: 'Key Result' },
  { id: 'kpi', label: 'KPI' },
];

function CreateOkrForm({ drivers, busy, initialMode = 'driver', initialDriverId = '', onSubmit, onCancel }) {
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [driverId, setDriverId] = useState(initialDriverId || drivers[0]?.id || '');
  const [objectiveId, setObjectiveId] = useState('');
  const [targetValue, setTargetValue] = useState('');
  const [currentValue, setCurrentValue] = useState('0');
  const [metricUnit, setMetricUnit] = useState('%');
  const [isFinancial, setIsFinancial] = useState(false);

  const objectivesForDriver = useMemo(() => {
    const driver = drivers.find((d) => d.id === driverId);
    return driver?.objectives || [];
  }, [drivers, driverId]);

  useEffect(() => {
    if (!driverId && drivers[0]?.id) setDriverId(drivers[0].id);
  }, [drivers, driverId]);

  useEffect(() => {
    if (objectivesForDriver.length) {
      setObjectiveId(objectivesForDriver[0].id);
    } else {
      setObjectiveId('');
    }
  }, [objectivesForDriver]);

  useEffect(() => {
    if (mode === 'kpi') setMetricUnit(isFinancial ? 'R$' : '');
    if (mode === 'kr') setMetricUnit('%');
  }, [mode, isFinancial]);

  return (
    <form
      className="space-y-3 rounded-2xl border border-chameleon/20 bg-white p-4 shadow-sm"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          mode,
          name,
          description,
          driverId,
          objectiveId,
          targetValue,
          currentValue,
          metricUnit,
          isFinancial,
        });
      }}
    >
      <div className="flex flex-wrap gap-2">
        {CREATE_MODES.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setMode(item.id)}
            className={[
              'rounded-lg px-3 py-1.5 text-xs font-bold transition',
              mode === item.id
                ? 'bg-chameleon text-white'
                : 'border border-slate-200 text-slate-600 hover:bg-slate-50',
            ].join(' ')}
          >
            {item.label}
          </button>
        ))}
      </div>

      {mode === 'driver' && (
        <>
          <label className="block text-xs font-semibold text-slate-600">
            Nome do direcionador
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Ex.: Experiência do Cliente"
            />
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Objetivo inicial (opcional)
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Descrição do objetivo associado"
            />
          </label>
        </>
      )}

      {mode === 'objective' && (
        <>
          <label className="block text-xs font-semibold text-slate-600">
            Direcionador
            <select
              required
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.sort_order}. {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Descrição do objetivo
            <textarea
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </>
      )}

      {mode === 'kr' && (
        <>
          <label className="block text-xs font-semibold text-slate-600">
            Direcionador
            <select
              required
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.sort_order}. {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Objetivo
            <select
              required
              value={objectiveId}
              onChange={(e) => setObjectiveId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              disabled={!objectivesForDriver.length}
            >
              {!objectivesForDriver.length && (
                <option value="">Crie um objetivo neste direcionador primeiro</option>
              )}
              {objectivesForDriver.map((obj) => (
                <option key={obj.id} value={obj.id}>
                  {obj.description.slice(0, 80)}
                  {obj.description.length > 80 ? '…' : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Descrição do KR
            <input
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-xs font-semibold text-slate-600">
              Alvo
              <input
                type="number"
                step="any"
                required
                value={targetValue}
                onChange={(e) => setTargetValue(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Valor atual
              <input
                type="number"
                step="any"
                value={currentValue}
                onChange={(e) => setCurrentValue(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Unidade
              <input
                value={metricUnit}
                onChange={(e) => setMetricUnit(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                placeholder="%"
              />
            </label>
          </div>
        </>
      )}

      {mode === 'kpi' && (
        <>
          <label className="block text-xs font-semibold text-slate-600">
            Direcionador
            <select
              required
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            >
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.sort_order}. {d.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold text-slate-600">
            Nome do KPI
            <input
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="sr-only"
              checked={isFinancial}
              onChange={(e) => setIsFinancial(e.target.checked)}
            />
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 items-center justify-center rounded border-2 ${
                isFinancial ? 'border-[#16a34a] bg-[#16a34a]' : 'border-slate-300 bg-white'
              }`}
            >
              {isFinancial && (
                <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 text-white" fill="currentColor">
                  <path d="M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z" />
                </svg>
              )}
            </span>
            KPI financeiro (ROI)
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-xs font-semibold text-slate-600">
              Alvo
              <input
                type="number"
                step="any"
                value={targetValue}
                onChange={(e) => setTargetValue(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Valor atual
              <input
                type="number"
                step="any"
                value={currentValue}
                onChange={(e) => setCurrentValue(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
            <label className="block text-xs font-semibold text-slate-600">
              Unidade
              <input
                value={metricUnit}
                onChange={(e) => setMetricUnit(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </label>
          </div>
        </>
      )}

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={busy || (mode === 'kr' && !objectiveId)}
          className="rounded-lg bg-chameleon px-4 py-2 text-sm font-bold text-white hover:bg-chameleon-dark disabled:opacity-50"
        >
          {busy ? 'Criando…' : 'Criar'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
        >
          Fechar
        </button>
      </div>
    </form>
  );
}

function DriverPanel({
  driver,
  open,
  onToggle,
  savingId,
  onUpdateKr,
  onUpdateKpi,
  onQuickCreate,
}) {
  const objectives = driver.objectives || [];
  const kpis = driver.kpis || [];
  const financialKpis = kpis.filter((k) => k.is_financial);
  const operationalKpis = kpis.filter((k) => !k.is_financial);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 bg-gradient-to-r from-chameleon/10 to-white px-5 py-4 text-left"
      >
        <div>
          <p className="text-[11px] font-bold uppercase tracking-wide text-chameleon-dark">
            Direcionador {driver.sort_order}
          </p>
          <h2 className="mt-0.5 text-base font-bold text-chameleon-dark">{driver.name}</h2>
        </div>
        <span className="text-sm font-bold text-chameleon-dark/60">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="space-y-5 border-t border-slate-100 px-5 py-5">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onQuickCreate('objective', driver.id)}
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-chameleon/40 hover:text-chameleon-dark"
            >
              + Objetivo
            </button>
            <button
              type="button"
              onClick={() => onQuickCreate('kr', driver.id)}
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-chameleon/40 hover:text-chameleon-dark"
            >
              + KR
            </button>
            <button
              type="button"
              onClick={() => onQuickCreate('kpi', driver.id)}
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:border-chameleon/40 hover:text-chameleon-dark"
            >
              + KPI
            </button>
          </div>

          <div className="space-y-4">
            <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
              Objetivos e Key Results
            </p>
            {!objectives.length && (
              <p className="text-sm text-slate-500">Nenhum objetivo neste direcionador.</p>
            )}
            {objectives.map((objective) => (
              <div key={objective.id} className="space-y-3 rounded-xl border border-slate-200 p-4">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                    Objetivo
                  </p>
                  <p className="mt-1 text-sm leading-relaxed text-slate-800">
                    {objective.description}
                  </p>
                </div>
                {(objective.key_results || []).map((kr) => (
                  <div key={kr.id} className="rounded-xl bg-slate-50/80 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900">{kr.description}</p>
                      <p className="text-xs font-bold text-chameleon-dark">
                        {formatMetric(kr.current_value, kr.metric_unit)} /{' '}
                        {formatMetric(kr.target_value, kr.metric_unit)}
                      </p>
                    </div>
                    <div className="mt-2">
                      <ProgressBar pct={kr.progress_pct} />
                      <p className="mt-1 text-[11px] text-slate-500">{kr.progress_pct}% do alvo</p>
                    </div>
                    <div className="mt-3">
                      <ValueEditor
                        label="KR"
                        current={kr.current_value}
                        target={kr.target_value}
                        unit={kr.metric_unit}
                        saving={savingId === kr.id}
                        onSave={(value) => onUpdateKr(kr.id, value)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {operationalKpis.map((kpi) => (
              <div key={kpi.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
                  KPI Operacional
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{kpi.name}</p>
                <p className="mt-2 text-lg font-bold text-slate-800">
                  {formatMetric(kpi.current_value, kpi.metric_unit)}
                </p>
                <div className="mt-3">
                  <ValueEditor
                    label="KPI"
                    current={kpi.current_value}
                    target={kpi.target_value}
                    unit={kpi.metric_unit}
                    saving={savingId === kpi.id}
                    onSave={(value) => onUpdateKpi(kpi.id, value)}
                  />
                </div>
              </div>
            ))}

            {financialKpis.map((kpi) => (
              <div
                key={kpi.id}
                className="rounded-xl border-2 border-amber-300/80 bg-gradient-to-br from-amber-50 via-yellow-50 to-white p-4 shadow-sm ring-1 ring-amber-200/60"
              >
                <p className="text-[11px] font-bold uppercase tracking-wide text-amber-700">
                  KPI Financeiro · ROI
                </p>
                <p className="mt-1 text-sm font-bold text-amber-950">{kpi.name}</p>
                <p className="mt-2 text-xl font-bold text-amber-800">
                  {formatMetric(kpi.current_value, kpi.metric_unit || 'R$')}
                </p>
                {Number(kpi.target_value) > 0 && (
                  <div className="mt-2">
                    <ProgressBar pct={kpi.progress_pct} tone="gold" />
                    <p className="mt-1 text-[11px] text-amber-700/80">
                      Alvo: {formatMetric(kpi.target_value, kpi.metric_unit || 'R$')}
                    </p>
                  </div>
                )}
                <div className="mt-3">
                  <ValueEditor
                    label="KPI"
                    current={kpi.current_value}
                    target={kpi.target_value}
                    unit={kpi.metric_unit || 'R$'}
                    saving={savingId === kpi.id}
                    onSave={(value) => onUpdateKpi(kpi.id, value)}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export default function OkrDashboard() {
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [savingId, setSavingId] = useState('');
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [createSeed, setCreateSeed] = useState({ mode: 'driver', driverId: '' });
  const [openMap, setOpenMap] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchOkrDashboard();
      const list = data.drivers || [];
      setDrivers(list);
    } catch (err) {
      setError(err.message || 'Erro ao carregar o Planejamento Estratégico.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(''), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  async function handleUpdateKr(krId, currentValue) {
    setSavingId(krId);
    setError('');
    try {
      const res = await updateOkrKeyResult(krId, { current_value: currentValue });
      const updated = res.key_result;
      setDrivers((prev) =>
        prev.map((driver) => ({
          ...driver,
          objectives: (driver.objectives || []).map((obj) => ({
            ...obj,
            key_results: (obj.key_results || []).map((kr) =>
              kr.id === updated.id ? updated : kr,
            ),
          })),
        })),
      );
      setToast('Key Result atualizado.');
    } catch (err) {
      setError(err.message || 'Falha ao atualizar KR.');
    } finally {
      setSavingId('');
    }
  }

  async function handleUpdateKpi(kpiId, currentValue) {
    setSavingId(kpiId);
    setError('');
    try {
      const res = await updateOkrKpi(kpiId, { current_value: currentValue });
      const updated = res.kpi;
      setDrivers((prev) =>
        prev.map((driver) => ({
          ...driver,
          kpis: (driver.kpis || []).map((kpi) => (kpi.id === updated.id ? updated : kpi)),
        })),
      );
      setToast('KPI atualizado.');
    } catch (err) {
      setError(err.message || 'Falha ao atualizar KPI.');
    } finally {
      setSavingId('');
    }
  }

  async function handleCreate(form) {
    setCreating(true);
    setError('');
    try {
      if (form.mode === 'driver') {
        await createOkrDriver({
          name: form.name.trim(),
          objective: form.description.trim() || undefined,
        });
        setToast('Direcionador criado.');
      } else if (form.mode === 'objective') {
        await createOkrObjective({
          driver_id: form.driverId,
          description: form.description.trim(),
        });
        setToast('Objetivo criado.');
      } else if (form.mode === 'kr') {
        await createOkrKeyResult({
          objective_id: form.objectiveId,
          description: form.description.trim(),
          target_value: Number(String(form.targetValue).replace(',', '.')),
          current_value: Number(String(form.currentValue || '0').replace(',', '.')),
          metric_unit: form.metricUnit || '%',
        });
        setToast('Key Result criado.');
      } else if (form.mode === 'kpi') {
        await createOkrKpi({
          driver_id: form.driverId,
          name: form.name.trim(),
          target_value: Number(String(form.targetValue || '0').replace(',', '.')),
          current_value: Number(String(form.currentValue || '0').replace(',', '.')),
          metric_unit: form.metricUnit || undefined,
          is_financial: Boolean(form.isFinancial),
        });
        setToast('KPI criado.');
      }
      setShowCreate(false);
      await load();
      if (form.driverId) {
        setOpenMap((prev) => ({ ...prev, [form.driverId]: true }));
      }
    } catch (err) {
      setError(err.message || 'Falha ao criar item.');
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Estratégia e Transformação Digital
          </p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Estratégia e OKRs</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-600">
            Todo cliente já nasce com os 5 direcionadores canônicos PanelDX (objetivos, KRs e KPIs
            sugeridos). Pode editar valores e criar itens novos associados a qualquer direcionador.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setCreateSeed({ mode: 'driver', driverId: drivers[0]?.id || '' });
            setShowCreate((v) => !v);
          }}
          className="rounded-lg bg-chameleon px-4 py-2 text-sm font-bold text-white hover:bg-chameleon-dark"
        >
          {showCreate ? 'Fechar formulário' : '+ Novo item OKR'}
        </button>
      </header>

      {showCreate && (
        <CreateOkrForm
          key={`${createSeed.mode}-${createSeed.driverId}`}
          drivers={drivers}
          busy={creating}
          initialMode={createSeed.mode}
          initialDriverId={createSeed.driverId}
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
        />
      )}

      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando matriz estratégica…</p>
      ) : (
        <div className="space-y-4">
          {drivers.map((driver) => (
            <DriverPanel
              key={driver.id}
              driver={driver}
              open={Boolean(openMap[driver.id])}
              onToggle={() =>
                setOpenMap((prev) => ({ ...prev, [driver.id]: !prev[driver.id] }))
              }
              savingId={savingId}
              onUpdateKr={handleUpdateKr}
              onUpdateKpi={handleUpdateKpi}
              onQuickCreate={(mode, driverId) => {
                setCreateSeed({ mode, driverId });
                setShowCreate(true);
              }}
            />
          ))}
          {!drivers.length && (
            <p className="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
              Nenhum direcionador encontrado. Crie o primeiro item OKR.
            </p>
          )}
        </div>
      )}

      {toast && (
        <div
          className="fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900 shadow-lg"
          role="status"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
