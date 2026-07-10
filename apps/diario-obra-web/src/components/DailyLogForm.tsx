import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createDailyLogDraft,
  fetchLogByDay,
  updateDailyLog,
} from '../api/rdoApi';
import {
  DEFAULT_EQUIPMENT,
  DEFAULT_SUPPLIES,
  DEFAULT_WORKFORCE,
  TABS,
  type TabId,
} from '../constants/rdo';
import { useVoiceDictation } from '../hooks/useVoiceDictation';
import {
  clearLocalDraft,
  loadLocalDraft,
  saveLocalDraft,
} from '../services/rdoDraftStorage';
import type {
  EquipmentRow,
  OccurrenceRow,
  ProjectSite,
  SupplyRow,
  WeatherPeriod,
  WorkforceRow,
} from '../types';
import OccurrencesPanel from './OccurrencesPanel';
import AgileDailyPanel, { dailyGoalAnswered, dailyGoalRequired } from './AgileDailyPanel';
import SiteConditionsCard, { endShiftComplete } from './SiteConditionsCard';
import MetricWithDetails from './ui/MetricWithDetails';
import VoiceTextarea from './ui/VoiceTextarea';
import YesNoWithDetails from './ui/YesNoWithDetails';

interface Props {
  site: ProjectSite;
  date: string;
  readOnly: boolean;
  onBack: () => void;
  onSaved: () => void;
}

const WEATHER_OPTIONS: { value: WeatherPeriod; label: string; icon: string }[] = [
  { value: 'SOL', label: 'Sol', icon: '☀️' },
  { value: 'CHUVA', label: 'Chuva', icon: '🌧️' },
  { value: 'NUBLADO', label: 'Nublado', icon: '☁️' },
];

function WeatherPicker({
  title,
  value,
  onChange,
  disabled,
}: {
  title: string;
  value: WeatherPeriod | null;
  onChange: (v: WeatherPeriod) => void;
  disabled?: boolean;
}) {
  return (
    <section className="mt-4">
      <h3 className="text-sm font-bold uppercase tracking-wide text-emerald-800">{title}</h3>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {WEATHER_OPTIONS.map((opt) => {
          const active = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={[
                'flex min-h-24 flex-col items-center justify-center rounded-2xl border-2 px-2 py-3 transition active:scale-[0.98] disabled:opacity-60',
                active
                  ? 'border-emerald-600 bg-emerald-600 text-white shadow-md'
                  : 'border-slate-200 bg-white text-slate-800',
              ].join(' ')}
            >
              <span className="text-3xl">{opt.icon}</span>
              <span className="mt-1 text-sm font-bold">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function mergeWorkforce(existing?: WorkforceRow[]) {
  const map = new Map((existing || []).map((w) => [w.role, w]));
  return DEFAULT_WORKFORCE.map((row) => {
    const saved = map.get(row.role) as
      | (WorkforceRow & { absences?: number; overtime_hours?: number })
      | undefined;
    return {
      ...row,
      headcount: saved?.headcount ?? 0,
      presence_details: saved?.presence_details ?? '',
      absences_count: saved?.absences_count ?? saved?.absences ?? 0,
      absences_details: saved?.absences_details ?? '',
      extra_hours_count: saved?.extra_hours_count ?? saved?.overtime_hours ?? 0,
      extra_hours_details: saved?.extra_hours_details ?? '',
      general_remarks: saved?.general_remarks ?? '',
    };
  });
}

function mergeSupplies(existing?: SupplyRow[]) {
  const map = new Map((existing || []).map((s) => [s.key, s]));
  return DEFAULT_SUPPLIES.map((row) => ({
    ...row,
    quantity: map.get(row.key)?.quantity ?? 0,
    details: map.get(row.key)?.details ?? '',
  }));
}

function mergeEquipment(existing?: EquipmentRow[]) {
  const byKey = new Map(
    (existing || []).filter((e) => e.key).map((e) => [e.key, e] as const),
  );
  const byNameStatus = new Map(
    (existing || []).map((e) => [`${e.equipment_name}:${e.status}`, e] as const),
  );
  return DEFAULT_EQUIPMENT.map((row) => {
    const saved = byKey.get(row.key) || byNameStatus.get(`${row.equipment_name}:${row.status}`);
    return {
      ...row,
      quantity: saved?.quantity ?? 0,
      remarks: saved?.remarks ?? '',
    };
  });
}

export default function DailyLogForm({ site, date, readOnly, onBack, onSaved }: Props) {
  const [tab, setTab] = useState<TabId>('Clima');
  const [logId, setLogId] = useState<string | null>(null);
  const [status, setStatus] = useState('Rascunho');
  const [loading, setLoading] = useState(true);
  const [weatherMorning, setWeatherMorning] = useState<WeatherPeriod | null>(null);
  const [weatherAfternoon, setWeatherAfternoon] = useState<WeatherPeriod | null>(null);
  const [technicalComments, setTechnicalComments] = useState('');
  const [workforce, setWorkforce] = useState<WorkforceRow[]>(DEFAULT_WORKFORCE);
  const [supplies, setSupplies] = useState<SupplyRow[]>(DEFAULT_SUPPLIES);
  const [equipment, setEquipment] = useState<EquipmentRow[]>(DEFAULT_EQUIPMENT);
  const [ppeCompliant, setPpeCompliant] = useState<boolean | null>(null);
  const [ppeDetails, setPpeDetails] = useState('');
  const [occurrences, setOccurrences] = useState<OccurrenceRow[]>([]);
  const [delayWaitingMaterial, setDelayWaitingMaterial] = useState(false);
  const [delayRework, setDelayRework] = useState(false);
  const [delayLackOfFront, setDelayLackOfFront] = useState(false);
  const [endShiftClean, setEndShiftClean] = useState<boolean | null>(null);
  const [endShiftToolsStored, setEndShiftToolsStored] = useState<boolean | null>(null);
  const [endShiftLooseMaterials, setEndShiftLooseMaterials] = useState<boolean | null>(null);
  const [sprintDailyGoal, setSprintDailyGoal] = useState('');
  const [sprintGoalLocked, setSprintGoalLocked] = useState(false);
  const [goalAchieved, setGoalAchieved] = useState<boolean | null>(null);
  const [impedimentDetails, setImpedimentDetails] = useState('');
  const [mitigationAction, setMitigationAction] = useState('');
  const [preventiveAction, setPreventiveAction] = useState('');
  const [saving, setSaving] = useState(false);
  const [signing, setSigning] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [serverEditable, setServerEditable] = useState<boolean | null>(null);

  const voice = useVoiceDictation();
  const editable = serverEditable !== null ? serverEditable : !readOnly;
  const [localDraftSavedAt, setLocalDraftSavedAt] = useState<string | null>(null);
  const skipAutoSaveRef = useRef(false);

  const applyLogToForm = useCallback((log: NonNullable<Awaited<ReturnType<typeof fetchLogByDay>>['log']>) => {
    setLogId(log.id);
    setStatus(log.status);
    setWeatherMorning(log.weather_morning || null);
    setWeatherAfternoon(log.weather_afternoon || null);
    setTechnicalComments(log.technical_comments || '');
    setWorkforce(mergeWorkforce(log.workforce));
    setSupplies(mergeSupplies(log.supplies));
    setEquipment(mergeEquipment(log.equipment_statuses));
    setPpeCompliant(log.ppe_compliant ?? null);
    setPpeDetails(log.ppe_compliant_details || '');
    setOccurrences(
      (log.occurrences || []).map((o) => ({
        type: o.type,
        exact_location: o.exact_location || '',
        what_happened: o.what_happened || (o as { description?: string }).description || '',
        immediate_action_taken: o.immediate_action_taken || '',
        safety_ppe_notes: o.safety_ppe_notes,
      })),
    );
    setDelayWaitingMaterial(Boolean(log.delay_waiting_material));
    setDelayRework(Boolean(log.delay_rework));
    setDelayLackOfFront(Boolean(log.delay_lack_of_front));
    setEndShiftClean(log.end_shift_clean ?? null);
    setEndShiftToolsStored(log.end_shift_tools_stored ?? null);
    setEndShiftLooseMaterials(log.end_shift_loose_materials ?? null);
    setSprintDailyGoal(log.sprint_daily_goal || '');
    setSprintGoalLocked(Boolean((log as { sprint_goal_locked?: boolean }).sprint_goal_locked));
    setGoalAchieved(log.goal_achieved ?? null);
    setImpedimentDetails(log.impediment_details || '');
    setMitigationAction(log.mitigation_action || '');
    setPreventiveAction(log.preventive_action || '');
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await fetchLogByDay(site.id, date);
        if (cancelled) return;
        const log = data.log;
        const local = loadLocalDraft(site.id, date);
        setServerEditable(
          typeof data.is_editable === 'boolean'
            ? data.is_editable
            : log?.is_editable ?? null,
        );

        if (log) {
          applyLogToForm(log);
          if (local?.saved_at) setLocalDraftSavedAt(local.saved_at);
        } else if (local?.payload) {
          const p = local.payload;
          setLogId(null);
          setStatus('Rascunho local');
          setServerEditable(true);
          setWeatherMorning((p.weather_morning as WeatherPeriod | null) || null);
          setWeatherAfternoon((p.weather_afternoon as WeatherPeriod | null) || null);
          setTechnicalComments(String(p.technical_comments || ''));
          if (Array.isArray(p.workforce)) setWorkforce(mergeWorkforce(p.workforce as WorkforceRow[]));
          if (Array.isArray(p.supplies)) setSupplies(mergeSupplies(p.supplies as SupplyRow[]));
          if (Array.isArray(p.equipment_statuses)) {
            setEquipment(mergeEquipment(p.equipment_statuses as EquipmentRow[]));
          }
          setPpeCompliant((p.ppe_compliant as boolean | null) ?? null);
          setPpeDetails(String(p.ppe_compliant_details || ''));
          if (Array.isArray(p.occurrences)) {
            setOccurrences(p.occurrences as OccurrenceRow[]);
          }
          setDelayWaitingMaterial(Boolean(p.delay_waiting_material));
          setDelayRework(Boolean(p.delay_rework));
          setDelayLackOfFront(Boolean(p.delay_lack_of_front));
          setEndShiftClean((p.end_shift_clean as boolean | null) ?? null);
          setEndShiftToolsStored((p.end_shift_tools_stored as boolean | null) ?? null);
          setEndShiftLooseMaterials((p.end_shift_loose_materials as boolean | null) ?? null);
          setSprintDailyGoal(String(p.sprint_daily_goal || ''));
          setSprintGoalLocked(Boolean(p.sprint_goal_locked));
          setGoalAchieved((p.goal_achieved as boolean | null) ?? null);
          setImpedimentDetails(String(p.impediment_details || ''));
          setMitigationAction(String(p.mitigation_action || ''));
          setPreventiveAction(String(p.preventive_action || ''));
          setLocalDraftSavedAt(local.saved_at);
        } else {
          setLogId(null);
          setStatus('—');
          setWorkforce(DEFAULT_WORKFORCE);
          setSupplies(DEFAULT_SUPPLIES);
          setEquipment(DEFAULT_EQUIPMENT);
        }
      } catch (err) {
        if (!cancelled) {
          const local = loadLocalDraft(site.id, date);
          if (local?.payload) {
            const p = local.payload;
            setServerEditable(true);
            setLogId(null);
            setStatus('Rascunho local (offline)');
            setWeatherMorning((p.weather_morning as WeatherPeriod | null) || null);
            setWeatherAfternoon((p.weather_afternoon as WeatherPeriod | null) || null);
            setTechnicalComments(String(p.technical_comments || ''));
            if (Array.isArray(p.workforce)) setWorkforce(mergeWorkforce(p.workforce as WorkforceRow[]));
            if (Array.isArray(p.supplies)) setSupplies(mergeSupplies(p.supplies as SupplyRow[]));
            if (Array.isArray(p.equipment_statuses)) {
              setEquipment(mergeEquipment(p.equipment_statuses as EquipmentRow[]));
            }
            setPpeCompliant((p.ppe_compliant as boolean | null) ?? null);
            setPpeDetails(String(p.ppe_compliant_details || ''));
            if (Array.isArray(p.occurrences)) setOccurrences(p.occurrences as OccurrenceRow[]);
            setDelayWaitingMaterial(Boolean(p.delay_waiting_material));
            setDelayRework(Boolean(p.delay_rework));
            setDelayLackOfFront(Boolean(p.delay_lack_of_front));
            setEndShiftClean((p.end_shift_clean as boolean | null) ?? null);
            setEndShiftToolsStored((p.end_shift_tools_stored as boolean | null) ?? null);
            setEndShiftLooseMaterials((p.end_shift_loose_materials as boolean | null) ?? null);
            setSprintDailyGoal(String(p.sprint_daily_goal || ''));
            setSprintGoalLocked(Boolean(p.sprint_goal_locked));
            setGoalAchieved((p.goal_achieved as boolean | null) ?? null);
            setImpedimentDetails(String(p.impediment_details || ''));
            setMitigationAction(String(p.mitigation_action || ''));
            setPreventiveAction(String(p.preventive_action || ''));
            setLocalDraftSavedAt(local.saved_at);
            setError('Sem conexão — exibindo rascunho salvo no celular.');
          } else {
            setError(err instanceof Error ? err.message : 'Erro ao carregar RDO.');
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [site.id, date, applyLogToForm]);

  useEffect(() => {
    if (!editable || loading || skipAutoSaveRef.current) return;
    const timer = window.setTimeout(() => {
      try {
        const payload = buildPayload();
        saveLocalDraft(site.id, date, payload);
        setLocalDraftSavedAt(new Date().toISOString());
      } catch {
        /* ignore draft build errors while typing */
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [
    editable,
    loading,
    site.id,
    date,
    weatherMorning,
    weatherAfternoon,
    technicalComments,
    workforce,
    supplies,
    equipment,
    ppeCompliant,
    ppeDetails,
    occurrences,
    delayWaitingMaterial,
    delayRework,
    delayLackOfFront,
    endShiftClean,
    endShiftToolsStored,
    endShiftLooseMaterials,
    sprintDailyGoal,
    goalAchieved,
    impedimentDetails,
    mitigationAction,
    preventiveAction,
  ]);

  function handleDictate(current: string, apply: (t: string) => void) {
    if (voice.isListening) {
      voice.stop();
      return;
    }
    voice.dictate(current, apply);
  }

  function patchWorkforce(idx: number, patch: Partial<WorkforceRow>) {
    setWorkforce((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }

  function buildPayload(extra: { finalize?: boolean } = {}) {
    const validOccurrences = occurrences.filter(
      (o) => o.what_happened?.trim() && (o.exact_location?.trim() || o.what_happened?.trim()),
    );
    return {
      project_id: site.id,
      date,
      weather_morning: weatherMorning,
      weather_afternoon: weatherAfternoon,
      technical_comments: technicalComments.trim() || undefined,
      ppe_compliant: ppeCompliant,
      ppe_compliant_details: ppeDetails.trim() || undefined,
      delay_waiting_material: delayWaitingMaterial,
      delay_rework: delayRework,
      delay_lack_of_front: delayLackOfFront,
      end_shift_clean: endShiftClean,
      end_shift_tools_stored: endShiftToolsStored,
      end_shift_loose_materials: endShiftLooseMaterials,
      ...(sprintGoalLocked ? {} : { sprint_daily_goal: sprintDailyGoal.trim() || undefined }),
      goal_achieved: goalAchieved,
      impediment_details: goalAchieved === false ? impedimentDetails.trim() || undefined : undefined,
      mitigation_action: goalAchieved === false ? mitigationAction.trim() || undefined : undefined,
      preventive_action: goalAchieved === false ? preventiveAction.trim() || undefined : undefined,
      workforce,
      supplies,
      equipment_statuses: equipment,
      occurrences: validOccurrences.map((o) => ({
        ...o,
        exact_location: o.exact_location?.trim() || 'Não informado',
        what_happened: o.what_happened.trim(),
        immediate_action_taken: o.immediate_action_taken?.trim() || undefined,
      })),
      ...extra,
      signed_by: extra.finalize ? 'Encarregado de obra' : undefined,
    };
  }

  async function handleSave() {
    if (!editable) return;
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const payload = buildPayload();
      if (logId) {
        await updateDailyLog(logId, payload);
      } else {
        const log = await createDailyLogDraft(payload);
        setLogId(log.id);
        setStatus(log.status);
      }
      setSuccess('Rascunho salvo.');
      clearLocalDraft(site.id, date);
      setLocalDraftSavedAt(null);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar.');
    } finally {
      setSaving(false);
    }
  }

  const requiresDaily = dailyGoalRequired({
    sprintDailyGoal,
    sprintGoalLocked,
    goalAchieved,
    impedimentDetails,
    mitigationAction,
    preventiveAction,
  });

  async function handleSign() {
    if (!editable) return;
    if (requiresDaily && !dailyGoalAnswered(goalAchieved)) {
      setError('Responda a Daily Ágil: atingiu o resultado de hoje?');
      return;
    }
    if (!endShiftComplete(endShiftClean, endShiftToolsStored, endShiftLooseMaterials)) {
      setError('Responda o Fechamento do Canteiro (as 3 perguntas) antes de assinar.');
      return;
    }
    setSigning(true);
    setError('');
    setSuccess('');

    try {
      const payload = buildPayload({ finalize: true });
      if (logId) {
        const log = await updateDailyLog(logId, payload);
        setStatus(log.status);
      } else {
        const log = await createDailyLogDraft(payload);
        setLogId(log.id);
        setStatus(log.status);
      }
      setSuccess('RDO assinado e finalizado.');
      clearLocalDraft(site.id, date);
      setLocalDraftSavedAt(null);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao assinar.');
    } finally {
      setSigning(false);
    }
  }

  const dateLabel = new Date(date + 'T12:00:00').toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
  });

  const voiceProps = {
    dictationSupported: voice.supported,
    isListening: voice.isListening,
    onDictate: handleDictate,
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-slate-200 bg-white px-2 pt-2">
        <div className="flex gap-1 overflow-x-auto pb-2">
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={[
                'shrink-0 rounded-full px-4 py-2 text-sm font-bold',
                tab === t ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700',
              ].join(' ')}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 pb-28">
        <button type="button" onClick={onBack} className="mb-2 text-sm font-semibold text-emerald-700">
          ← Voltar ao calendário
        </button>

        <div className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">{site.name}</p>
          <p className="text-lg font-bold capitalize text-slate-900">{dateLabel}</p>
          <p className="mt-1 text-sm">
            Status: <strong>{status}</strong>
            {localDraftSavedAt && editable && (
              <span className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                Rascunho local salvo
              </span>
            )}
            {readOnly && (
              <span className="ml-2 rounded bg-slate-200 px-2 py-0.5 text-xs font-bold text-slate-700">
                Somente leitura
              </span>
            )}
          </p>
          {!editable && !localDraftSavedAt && status !== 'Rascunho local' && status !== 'Rascunho local (offline)' && (
            <p className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-700">
              {status === 'Assinado' || status === 'Sincronizado' ? (
                <>
                  Este dia já foi <strong>assinado e fechado</strong>. Para editar de novo, o gestor
                  precisa usar <strong>Reabrir dia</strong> em Relatórios Operacionais.
                </>
              ) : (
                <>
                  Este dia está <strong>somente leitura</strong>. Preencha o <strong>dia de hoje</strong>{' '}
                  no calendário ou peça ao gestor para reabrir um dia anterior.
                </>
              )}
            </p>
          )}
        </div>

        {loading ? (
          <p className="mt-6 text-center text-sm text-slate-500">Carregando RDO…</p>
        ) : (
          <>
            {tab === 'Clima' && (
              <>
                <WeatherPicker
                  title="Clima — Manhã"
                  value={weatherMorning}
                  onChange={setWeatherMorning}
                  disabled={!editable}
                />
                <WeatherPicker
                  title="Clima — Tarde"
                  value={weatherAfternoon}
                  onChange={setWeatherAfternoon}
                  disabled={!editable}
                />
                <VoiceTextarea
                  label="Observações técnicas"
                  value={technicalComments}
                  onChange={setTechnicalComments}
                  disabled={!editable}
                  dictationSupported={voice.supported}
                  isListening={voice.isListening}
                  onDictate={handleDictate}
                  placeholder="Fiscalização, visitas, orientações…"
                />
              </>
            )}

            {tab === 'Efetivo' && (
              <div className="mt-4 space-y-4">
                {workforce.map((row, idx) => (
                  <section key={row.role} className="space-y-2">
                    <h3 className="px-1 text-base font-bold text-slate-900">{row.role}</h3>
                    <MetricWithDetails
                      label="Presenças"
                      value={row.headcount}
                      disabled={!editable}
                      details={row.presence_details}
                      onChange={(v) => patchWorkforce(idx, { headcount: v })}
                      onDetailsChange={(t) => patchWorkforce(idx, { presence_details: t })}
                      detailsPlaceholder="Ex: Nomes, equipes, terceirizadas…"
                      {...voiceProps}
                    />
                    <MetricWithDetails
                      label="Faltas"
                      value={row.absences_count}
                      disabled={!editable}
                      details={row.absences_details}
                      onChange={(v) => patchWorkforce(idx, { absences_count: v })}
                      onDetailsChange={(t) => patchWorkforce(idx, { absences_details: t })}
                      detailsPlaceholder="Ex: Quem faltou? Motivo?"
                      {...voiceProps}
                    />
                    <MetricWithDetails
                      label="Horas extras"
                      value={row.extra_hours_count}
                      disabled={!editable}
                      details={row.extra_hours_details}
                      onChange={(v) => patchWorkforce(idx, { extra_hours_count: v })}
                      onDetailsChange={(t) => patchWorkforce(idx, { extra_hours_details: t })}
                      detailsPlaceholder="Ex: Quem fez hora extra? Quantas horas?"
                      {...voiceProps}
                    />
                    {(row.headcount > 0 ||
                      row.absences_count > 0 ||
                      row.extra_hours_count > 0 ||
                      row.general_remarks) && (
                      <VoiceTextarea
                        label="Observações gerais"
                        value={row.general_remarks || ''}
                        onChange={(t) => patchWorkforce(idx, { general_remarks: t })}
                        disabled={!editable}
                        dictationSupported={voice.supported}
                        isListening={voice.isListening}
                        onDictate={handleDictate}
                        placeholder="Outras anotações sobre esta função…"
                      />
                    )}
                  </section>
                ))}
              </div>
            )}

            {tab === 'Segurança' && (
              <div className="mt-4 space-y-3">
                <YesNoWithDetails
                  label="A galera estava de EPI certinho?"
                  value={ppeCompliant}
                  onChange={setPpeCompliant}
                  details={ppeDetails}
                  onDetailsChange={setPpeDetails}
                  detailsPlaceholder="Quem estava sem? Qual peça faltou?"
                  disabled={!editable}
                  dictationSupported={voice.supported}
                  isListening={voice.isListening}
                  onDictate={handleDictate}
                />
              </div>
            )}

            {tab === 'Ocorrências' && (
              <OccurrencesPanel
                occurrences={occurrences}
                onChange={setOccurrences}
                disabled={!editable}
                dictationSupported={voice.supported}
                isListening={voice.isListening}
                onDictate={handleDictate}
              />
            )}

            {tab === 'Insumos' && (
              <div className="mt-4 space-y-4">
                <section className="space-y-2">
                  <h3 className="px-1 text-sm font-bold uppercase tracking-wide text-emerald-800">
                    Materiais
                  </h3>
                  {supplies.map((row, idx) => (
                    <MetricWithDetails
                      key={row.key}
                      label={`${row.label} (${row.unit})`}
                      value={row.quantity}
                      disabled={!editable}
                      details={row.details}
                      onChange={(v) =>
                        setSupplies((prev) =>
                          prev.map((s, i) => (i === idx ? { ...s, quantity: v } : s)),
                        )
                      }
                      onDetailsChange={(t) =>
                        setSupplies((prev) =>
                          prev.map((s, i) => (i === idx ? { ...s, details: t } : s)),
                        )
                      }
                      detailsPlaceholder="Ex: Fornecedor, lote, destino no canteiro…"
                      {...voiceProps}
                    />
                  ))}
                </section>

                <section className="space-y-2">
                  <h3 className="px-1 text-sm font-bold uppercase tracking-wide text-emerald-800">
                    Equipamentos
                  </h3>
                  {equipment.map((row, idx) => (
                    <MetricWithDetails
                      key={row.key}
                      label={
                        row.status === 'Operando'
                          ? `${row.label} — em operação`
                          : `${row.label} — parado / quebrado`
                      }
                      value={row.quantity}
                      disabled={!editable}
                      details={row.remarks}
                      onChange={(v) =>
                        setEquipment((prev) =>
                          prev.map((e, i) => (i === idx ? { ...e, quantity: v } : e)),
                        )
                      }
                      onDetailsChange={(t) =>
                        setEquipment((prev) =>
                          prev.map((e, i) => (i === idx ? { ...e, remarks: t } : e)),
                        )
                      }
                      detailsPlaceholder={
                        row.status === 'Operando'
                          ? 'Ex: Qual equipamento? Atividade…'
                          : 'Ex: Quais máquinas? Motivo da parada?'
                      }
                      {...voiceProps}
                    />
                  ))}
                </section>
              </div>
            )}

            {tab === 'Daily Ágil' && (
              <AgileDailyPanel
                sprintDailyGoal={sprintDailyGoal}
                goalAchieved={goalAchieved}
                impedimentDetails={impedimentDetails}
                mitigationAction={mitigationAction}
                preventiveAction={preventiveAction}
                onSprintDailyGoalChange={setSprintDailyGoal}
                onGoalAchievedChange={setGoalAchieved}
                onImpedimentDetailsChange={setImpedimentDetails}
                onMitigationActionChange={setMitigationAction}
                onPreventiveActionChange={setPreventiveAction}
                sprintGoalLocked={sprintGoalLocked}
                disabled={!editable}
                dictationSupported={voice.supported}
                isListening={voice.isListening}
                onDictate={handleDictate}
              />
            )}
          </>
        )}

        {!loading && (
          <SiteConditionsCard
            delayWaitingMaterial={delayWaitingMaterial}
            delayRework={delayRework}
            delayLackOfFront={delayLackOfFront}
            endShiftClean={endShiftClean}
            endShiftToolsStored={endShiftToolsStored}
            endShiftLooseMaterials={endShiftLooseMaterials}
            onDelayWaitingMaterial={setDelayWaitingMaterial}
            onDelayRework={setDelayRework}
            onDelayLackOfFront={setDelayLackOfFront}
            onEndShiftClean={setEndShiftClean}
            onEndShiftToolsStored={setEndShiftToolsStored}
            onEndShiftLooseMaterials={setEndShiftLooseMaterials}
            disabled={!editable}
          />
        )}

        {voice.status && <p className="mt-2 text-xs text-emerald-700">{voice.status}</p>}
        {error && <p className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        {success && (
          <p className="mt-4 rounded-xl bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
            {success}
          </p>
        )}
      </div>

      {editable && (
        <div
          className="shrink-0 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur"
          style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
        >
          <button
            type="button"
            onClick={onBack}
            className="mb-2 w-full min-h-11 rounded-2xl border-2 border-slate-300 bg-slate-50 text-sm font-bold text-slate-800"
          >
            📅 Calendário
          </button>
          <button
            type="button"
            disabled={saving || signing || loading || !weatherMorning || !weatherAfternoon}
            onClick={handleSave}
            className="mb-2 w-full min-h-12 rounded-2xl border-2 border-emerald-600 bg-white text-base font-bold text-emerald-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? 'Salvando…' : 'Salvar Rascunho'}
          </button>
          <button
            type="button"
            disabled={
              saving ||
              signing ||
              loading ||
              !weatherMorning ||
              !weatherAfternoon ||
              (requiresDaily && !dailyGoalAnswered(goalAchieved)) ||
              !endShiftComplete(endShiftClean, endShiftToolsStored, endShiftLooseMaterials)
            }
            onClick={handleSign}
            className="w-full min-h-14 rounded-2xl bg-emerald-600 text-lg font-bold text-white shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {signing ? 'Assinando…' : 'Finalizar e Assinar'}
          </button>
          {requiresDaily && !dailyGoalAnswered(goalAchieved) && (
            <p className="mt-2 text-center text-xs text-amber-800">
              Responda a Daily Ágil (meta atingida?) para habilitar a assinatura.
            </p>
          )}
          {(!requiresDaily || dailyGoalAnswered(goalAchieved)) &&
            !endShiftComplete(endShiftClean, endShiftToolsStored, endShiftLooseMaterials) && (
            <p className="mt-2 text-center text-xs text-amber-800">
              Responda o Fechamento do Canteiro para habilitar a assinatura.
            </p>
          )}
        </div>
      )}

      {!editable && (
        <div
          className="shrink-0 border-t border-slate-200 bg-white/95 px-4 py-3 backdrop-blur"
          style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
        >
          <button
            type="button"
            onClick={onBack}
            className="w-full min-h-11 rounded-2xl border-2 border-slate-300 bg-slate-50 text-sm font-bold text-slate-800"
          >
            📅 Calendário
          </button>
        </div>
      )}
    </div>
  );
}
