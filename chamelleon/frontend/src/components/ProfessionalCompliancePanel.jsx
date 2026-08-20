import { useCallback, useEffect, useState } from 'react';
import {
  createHealthRecord,
  createTrainingRecord,
  deleteHealthRecord,
  deleteTrainingRecord,
  listHealthRecords,
  listTrainingRecords,
} from '../services/complianceApi';

const TRAINING_TYPES = [
  'Admissional',
  'Periodico',
  'NR-35',
  'NR-10',
  'NR-12',
  'NR-33',
  'Outro',
];

const EXAM_TYPES = [
  'Admissional',
  'Periodico',
  'Demissional',
  'Mudanca_Risco',
  'Retorno_Trabalho',
];

const STATUS_CLASS = {
  valido: 'bg-emerald-100 text-emerald-800',
  a_vencer: 'bg-amber-100 text-amber-900',
  vencido: 'bg-red-100 text-red-800',
  sem_validade: 'bg-slate-100 text-slate-600',
};

const EMPTY_TRAINING = {
  training_type: 'NR-35',
  custom_label: '',
  completed_at: '',
  expires_at: '',
  hours: '',
  notes: '',
};

const EMPTY_HEALTH = {
  exam_type: 'Periodico',
  exam_date: '',
  expires_at: '',
  result: 'Apto',
  notes: '',
};

export default function ProfessionalCompliancePanel({ professional, onClose }) {
  const [trainings, setTrainings] = useState([]);
  const [health, setHealth] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [trainingForm, setTrainingForm] = useState(EMPTY_TRAINING);
  const [healthForm, setHealthForm] = useState(EMPTY_HEALTH);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!professional?.id) return;
    setLoading(true);
    setError('');
    try {
      const [tRes, hRes] = await Promise.all([
        listTrainingRecords(professional.id),
        listHealthRecords(professional.id),
      ]);
      setTrainings(tRes.records || []);
      setHealth(hRes.records || []);
    } catch (err) {
      setError(err.message || 'Erro ao carregar conformidade.');
    } finally {
      setLoading(false);
    }
  }, [professional?.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleAddTraining(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await createTrainingRecord({
        professional_id: professional.id,
        training_type: trainingForm.training_type,
        custom_label: trainingForm.custom_label || null,
        completed_at: trainingForm.completed_at,
        expires_at: trainingForm.expires_at || null,
        hours: trainingForm.hours === '' ? null : Number(trainingForm.hours),
        notes: trainingForm.notes || null,
      });
      setTrainingForm(EMPTY_TRAINING);
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao salvar treinamento.');
    } finally {
      setSaving(false);
    }
  }

  async function handleAddHealth(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await createHealthRecord({
        professional_id: professional.id,
        exam_type: healthForm.exam_type,
        exam_date: healthForm.exam_date,
        expires_at: healthForm.expires_at || null,
        result: healthForm.result,
        notes: healthForm.notes || null,
      });
      setHealthForm(EMPTY_HEALTH);
      await load();
    } catch (err) {
      setError(err.message || 'Erro ao salvar exame.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/50 p-4 sm:items-center">
      <button type="button" className="absolute inset-0" aria-label="Fechar" onClick={onClose} />
      <div className="relative z-10 max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <header className="sticky top-0 border-b border-slate-100 bg-white px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Conformidade
          </p>
          <h2 className="text-lg font-bold text-slate-900">{professional.name}</h2>
          <p className="text-xs text-slate-500">{professional.role}</p>
        </header>

        <div className="space-y-6 px-5 py-5">
          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
          {loading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : (
            <>
              <section>
                <h3 className="text-sm font-semibold text-slate-800">Treinamentos</h3>
                <ul className="mt-2 space-y-2">
                  {trainings.length === 0 && (
                    <li className="text-xs text-slate-500">Nenhum treinamento cadastrado.</li>
                  )}
                  {trainings.map((row) => (
                    <li
                      key={row.id}
                      className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-slate-800">
                          {row.training_type}
                          {row.custom_label ? ` — ${row.custom_label}` : ''}
                        </p>
                        <p className="text-xs text-slate-500">
                          Concluído {row.completed_at}
                          {row.expires_at ? ` · Validade ${row.expires_at}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_CLASS[row.status] || STATUS_CLASS.sem_validade}`}
                        >
                          {row.status}
                        </span>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          onClick={async () => {
                            await deleteTrainingRecord(row.id);
                            await load();
                          }}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                <form onSubmit={handleAddTraining} className="mt-3 grid gap-2 sm:grid-cols-2">
                  <select
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={trainingForm.training_type}
                    onChange={(e) =>
                      setTrainingForm((f) => ({ ...f, training_type: e.target.value }))
                    }
                  >
                    {TRAINING_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <input
                    type="date"
                    required
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={trainingForm.completed_at}
                    onChange={(e) =>
                      setTrainingForm((f) => ({ ...f, completed_at: e.target.value }))
                    }
                  />
                  <input
                    type="date"
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={trainingForm.expires_at}
                    onChange={(e) =>
                      setTrainingForm((f) => ({ ...f, expires_at: e.target.value }))
                    }
                    placeholder="Validade"
                  />
                  {trainingForm.training_type === 'Outro' && (
                    <input
                      className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                      value={trainingForm.custom_label}
                      onChange={(e) =>
                        setTrainingForm((f) => ({ ...f, custom_label: e.target.value }))
                      }
                      placeholder="Rótulo"
                      required
                    />
                  )}
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-lg bg-chameleon px-3 py-2 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2"
                  >
                    Adicionar treinamento
                  </button>
                </form>
              </section>

              <section>
                <h3 className="text-sm font-semibold text-slate-800">Exames / ASO</h3>
                <ul className="mt-2 space-y-2">
                  {health.length === 0 && (
                    <li className="text-xs text-slate-500">Nenhum exame cadastrado.</li>
                  )}
                  {health.map((row) => (
                    <li
                      key={row.id}
                      className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-slate-800">
                          {row.exam_type} · {row.result}
                        </p>
                        <p className="text-xs text-slate-500">
                          {row.exam_date}
                          {row.expires_at ? ` · Validade ${row.expires_at}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${STATUS_CLASS[row.status] || STATUS_CLASS.sem_validade}`}
                        >
                          {row.status}
                        </span>
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          onClick={async () => {
                            await deleteHealthRecord(row.id);
                            await load();
                          }}
                        >
                          Excluir
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
                <form onSubmit={handleAddHealth} className="mt-3 grid gap-2 sm:grid-cols-2">
                  <select
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={healthForm.exam_type}
                    onChange={(e) => setHealthForm((f) => ({ ...f, exam_type: e.target.value }))}
                  >
                    {EXAM_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <select
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={healthForm.result}
                    onChange={(e) => setHealthForm((f) => ({ ...f, result: e.target.value }))}
                  >
                    <option value="Apto">Apto</option>
                    <option value="Inapto">Inapto</option>
                  </select>
                  <input
                    type="date"
                    required
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={healthForm.exam_date}
                    onChange={(e) => setHealthForm((f) => ({ ...f, exam_date: e.target.value }))}
                  />
                  <input
                    type="date"
                    className="rounded-lg border border-slate-300 px-2 py-2 text-sm"
                    value={healthForm.expires_at}
                    onChange={(e) => setHealthForm((f) => ({ ...f, expires_at: e.target.value }))}
                  />
                  <button
                    type="submit"
                    disabled={saving}
                    className="rounded-lg bg-chameleon px-3 py-2 text-sm font-semibold text-white disabled:opacity-60 sm:col-span-2"
                  >
                    Adicionar exame/ASO
                  </button>
                </form>
              </section>
            </>
          )}
        </div>

        <footer className="border-t border-slate-100 px-5 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600"
          >
            Fechar
          </button>
        </footer>
      </div>
    </div>
  );
}
