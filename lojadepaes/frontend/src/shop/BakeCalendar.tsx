import { useEffect, useMemo, useState } from "react";
import { BreadStrokeIcon } from "../components/HeaderIcons";
import { DateRequestForm } from "./DateRequestForm";
import { isDaySelectable, isProductionDay, showsBreadIcon } from "./calendarDays";
import { previewCalendar, type CalendarDay, type CalendarLine, type CalendarPreview } from "./calendarApi";
import { trackEvent } from "./tracking";

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

type Props = {
  lines: CalendarLine[];
  selectedDate?: string | null;
  onSelectDate?: (date: string) => void;
  onSelectedDayChange?: (day: CalendarDay | null) => void;
  layout?: "shelf" | "checkout";
};

function monthLabel(year: number, month: number): string {
  const raw = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(
    new Date(year, month, 1),
  );
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function isoDate(year: number, month: number, day: number): string {
  const value = new Date(Date.UTC(year, month, day));
  return value.toISOString().slice(0, 10);
}

function shiftMonth(year: number, month: number, delta: number): { year: number; month: number } {
  const date = new Date(year, month + delta, 1);
  return { year: date.getFullYear(), month: date.getMonth() };
}

export function BakeCalendar({
  lines,
  selectedDate,
  onSelectDate,
  onSelectedDayChange,
  layout = "checkout",
}: Props) {
  const today = new Date();
  const [cursor, setCursor] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const [internalSelected, setInternalSelected] = useState<string | null>(null);
  const selected = selectedDate !== undefined ? selectedDate : internalSelected;
  const [data, setData] = useState<CalendarPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const range = useMemo(() => {
    const start = isoDate(cursor.year, cursor.month, 1);
    const endDate = new Date(cursor.year, cursor.month + 1, 0);
    const end = isoDate(endDate.getFullYear(), endDate.getMonth(), endDate.getDate());
    return { start, end };
  }, [cursor]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    previewCalendar({
      start: range.start,
      end: range.end,
      selected,
      lines,
    })
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("Não foi possível consultar as fornadas agora.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [attempt, lines, range.end, range.start, selected]);

  const byDate = new Map((data?.days ?? []).map((day) => [day.date, day]));
  const firstWeekday = new Date(cursor.year, cursor.month, 1).getDay();
  const mondayOffset = firstWeekday === 0 ? 6 : firstWeekday - 1;
  const daysInMonth = new Date(cursor.year, cursor.month + 1, 0).getDate();
  const cells: Array<{ date: string; day: CalendarDay | null } | null> = [
    ...Array.from({ length: mondayOffset }, () => null),
    ...Array.from({ length: daysInMonth }, (_, index) => {
      const date = isoDate(cursor.year, cursor.month, index + 1);
      return { date, day: byDate.get(date) ?? null };
    }),
  ];

  const selectedDay = data?.days.find((day) => day.date === selected) ?? null;
  const productionDays = (data?.days ?? []).filter((day) => isProductionDay(day));
  const selectableDays = productionDays.filter((day) => isDaySelectable(day));
  const hasCapacityLegend = productionDays.some((day) => day.at_capacity);
  const hasFullLegend = productionDays.some((day) => day.status === "full");
  const hasSameDayLegend = (data?.days ?? []).some((day) => day.status === "same_day");
  const cartCount = lines.reduce((total, line) => total + line.quantity, 0);

  useEffect(() => {
    onSelectedDayChange?.(selectedDay);
  }, [onSelectedDayChange, selectedDay]);

  function choose(day: CalendarDay) {
    if (!isDaySelectable(day)) {
      return;
    }
    if (onSelectDate) {
      onSelectDate(day.date);
    } else {
      setInternalSelected(day.date);
    }
    trackEvent("fornada_escolher", { dados: { data_fornada: day.date } });
  }

  return (
    <div className={`bake-calendar bake-calendar--${layout}`} aria-labelledby="bake-calendar-title">
      {layout === "shelf" ? null : <p className="eyebrow">Agenda de A Loja</p>}
      <h3 id="bake-calendar-title">{layout === "shelf" ? "Escolha sua fornada" : "Escolha sua próxima fornada"}</h3>
      <div className="calendar-head">
        <button
          type="button"
          aria-label="Mês anterior"
          onClick={() => setCursor((current) => shiftMonth(current.year, current.month, -1))}
        >
          ‹
        </button>
        <p>{monthLabel(cursor.year, cursor.month)}</p>
        <button
          type="button"
          aria-label="Próximo mês"
          onClick={() => setCursor((current) => shiftMonth(current.year, current.month, 1))}
        >
          ›
        </button>
      </div>
      <div className="bake-calendar-grid" role="grid" aria-label="Calendário de fornadas">
        {WEEKDAYS.map((label) => (
          <span key={label}>{label}</span>
        ))}
        {cells.map((cell, index) => {
          if (cell === null) {
            return (
              <span key={`pad-${index}`} className="day bake-day is-empty" aria-hidden="true">
                <span className="bake-day-icon" />
                <span />
              </span>
            );
          }
          const day = cell.day;
          if (day === null) {
            return (
              <span key={cell.date} className="day bake-day is-empty">
                <span className="bake-day-icon" />
                <span>{Number(cell.date.slice(8))}</span>
              </span>
            );
          }
          const showBread = showsBreadIcon(day, loading, Boolean(error));
          const selectedClass = selected === day.date ? " is-chosen" : "";
          const capacityClass = day.at_capacity ? " is-at-capacity" : "";
          return (
            <button
              key={day.date}
              type="button"
              className={`day bake-day is-${day.status}${capacityClass}${selectedClass}`}
              aria-label={day.accessible_label}
              aria-pressed={selected === day.date}
              disabled={!isDaySelectable(day) || loading}
              onClick={() => choose(day)}
            >
              <span className="bake-day-icon">{showBread ? <BreadStrokeIcon size={16} /> : null}</span>
              <span>{Number(day.date.slice(8))}</span>
            </button>
          );
        })}
      </div>
      {!loading && !error ? (
        <p className="bake-calendar-legend">
          <span className="bake-day-icon" aria-hidden="true">
            <BreadStrokeIcon size={16} />
          </span>
          Dia de produção aberto
        </p>
      ) : null}
      {!loading && !error && hasCapacityLegend ? (
        <p className="bake-calendar-legend is-at-capacity">
          <span className="bake-day-icon" aria-hidden="true">
            <BreadStrokeIcon size={16} />
          </span>
          Fornada no limite
        </p>
      ) : null}
      {!loading && !error && hasFullLegend ? (
        <p className="bake-calendar-legend is-full">Fornada completa</p>
      ) : null}
      {!loading && !error && hasSameDayLegend ? (
        <p className="bake-calendar-legend">Pedidos pelo calendário são para os próximos dias</p>
      ) : null}
      <DateRequestForm selectedDate={selected} lines={lines} cartCount={cartCount} />
      {loading ? <p className="bake-calendar-note">Consultando as fornadas…</p> : null}
      {error ? (
        <p className="bake-calendar-note" role="alert">
          {error}{" "}
          <button type="button" className="text-button" onClick={() => setAttempt((current) => current + 1)}>
            Tentar o calendário de novo
          </button>
        </p>
      ) : null}
      {!loading && !error && productionDays.length === 0 ? (
        <p className="bake-calendar-selected">
          Não há dia de produção neste mês. Use as setas para ver o próximo mês disponível.
        </p>
      ) : null}
      {!loading && !error && productionDays.length > 0 && selectableDays.length === 0 ? (
        <p className="bake-calendar-selected">
          Não há fornada disponível neste mês para este pedido. Use as setas para ver outra data.
        </p>
      ) : null}
      {selected ? (
        <p className="bake-calendar-selected">
          {selectedDay ? selectedDay.accessible_label : `Data escolhida: ${selected}`}
        </p>
      ) : null}
      {!loading && !error && !selected && selectableDays.length > 0 ? (
        <p className="bake-calendar-selected">Escolha um dia com o ícone de pão.</p>
      ) : null}
      {layout !== "shelf" && data?.notice && !error ? (
        <p className="bake-calendar-note">{data.notice}</p>
      ) : null}
      {data?.review_message && !error ? <p className="bake-calendar-note">{data.review_message}</p> : null}
      {data?.full_message && !error ? <p className="bake-calendar-note">{data.full_message}</p> : null}
      {layout !== "shelf" && data?.alternatives.length ? (
        <div className="bake-calendar-alts">
          {data.alternatives.map((item) => (
            <button key={item.date} type="button" className="time" onClick={() => (onSelectDate ? onSelectDate(item.date) : setInternalSelected(item.date))}>
              {item.accessible_label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
