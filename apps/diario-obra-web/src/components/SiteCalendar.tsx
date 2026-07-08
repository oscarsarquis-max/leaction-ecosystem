import { useEffect, useMemo, useState } from 'react';
import { fetchMonthCalendar } from '../api/rdoApi';
import type { CalendarDay, ProjectSite } from '../types';

interface Props {
  site: ProjectSite;
  onBack: () => void;
  onOpenDay: (day: CalendarDay) => void;
}

const WEEKDAYS = ['D', 'S', 'T', 'Q', 'Q', 'S', 'S'];

function statusColor(status: CalendarDay['calendar_status']) {
  if (status === 'finalized') return 'bg-emerald-600 text-white border-emerald-700';
  if (status === 'draft') return 'bg-amber-400 text-amber-950 border-amber-500';
  return 'bg-slate-200 text-slate-600 border-slate-300';
}

export default function SiteCalendar({ site, onBack, onOpenDay }: Props) {
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const monthLabel = useMemo(
    () =>
      new Date(cursor.year, cursor.month - 1, 1).toLocaleDateString('pt-BR', {
        month: 'long',
        year: 'numeric',
      }),
    [cursor],
  );

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await fetchMonthCalendar(site.id, cursor.year, cursor.month);
      setDays(data.days);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar calendário.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [site.id, cursor.year, cursor.month]);

  const firstWeekday = new Date(cursor.year, cursor.month - 1, 1).getDay();
  const blanks = Array.from({ length: firstWeekday });
  const todayIso = new Date().toISOString().slice(0, 10);

  function shiftMonth(delta: number) {
    const d = new Date(cursor.year, cursor.month - 1 + delta, 1);
    setCursor({ year: d.getFullYear(), month: d.getMonth() + 1 });
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <button type="button" onClick={onBack} className="mb-3 text-sm font-semibold text-emerald-700">
          ← Trocar canteiro
        </button>

        <div className="rounded-2xl border border-emerald-100 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-bold text-slate-900">{site.name}</h2>
          <p className="text-sm text-slate-500">Calendário de RDO — toque no dia</p>

          <div className="mt-4 flex items-center justify-between">
            <button
              type="button"
              onClick={() => shiftMonth(-1)}
              className="min-h-10 rounded-xl bg-slate-100 px-3 font-bold text-slate-700"
            >
              ‹
            </button>
            <p className="text-sm font-bold capitalize text-emerald-800">{monthLabel}</p>
            <button
              type="button"
              onClick={() => shiftMonth(1)}
              className="min-h-10 rounded-xl bg-slate-100 px-3 font-bold text-slate-700"
            >
              ›
            </button>
          </div>

          <div className="mt-3 grid grid-cols-7 gap-1 text-center text-xs font-bold text-slate-500">
            {WEEKDAYS.map((w) => (
              <span key={w}>{w}</span>
            ))}
          </div>

          {loading ? (
            <p className="mt-6 text-center text-sm text-slate-500">Carregando…</p>
          ) : (
            <div className="mt-2 grid grid-cols-7 gap-1">
              {blanks.map((_, i) => (
                <div key={`b-${i}`} />
              ))}
              {days.map((day) => {
                const num = Number(day.date.slice(8, 10));
                const isToday = day.date === todayIso;
                return (
                  <button
                    key={day.date}
                    type="button"
                    onClick={() => onOpenDay(day)}
                    className={[
                      'flex aspect-square flex-col items-center justify-center rounded-xl border text-sm font-bold transition active:scale-95',
                      statusColor(day.calendar_status),
                      isToday ? 'ring-2 ring-emerald-500 ring-offset-1' : '',
                    ].join(' ')}
                  >
                    {num}
                  </button>
                );
              })}
            </div>
          )}

          <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-600">
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded bg-emerald-600" /> Finalizado
            </span>
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded bg-amber-400" /> Rascunho
            </span>
            <span className="flex items-center gap-1">
              <span className="h-3 w-3 rounded bg-slate-200" /> Sem RDO
            </span>
          </div>

          {error && (
            <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
          )}
        </div>
      </div>
    </div>
  );
}
