export const WEEKDAYS = [
  { id: 1, short: "Seg", name: "Segunda-feira" },
  { id: 2, short: "Ter", name: "Terça-feira" },
  { id: 3, short: "Qua", name: "Quarta-feira" },
  { id: 4, short: "Qui", name: "Quinta-feira" },
  { id: 5, short: "Sex", name: "Sexta-feira" },
  { id: 6, short: "Sáb", name: "Sábado" },
  { id: 7, short: "Dom", name: "Domingo" },
] as const;

type Props = {
  selected: number[];
  onChange: (next: number[]) => void;
  disabled?: boolean;
};

export function WeekdayPicker({ selected, onChange, disabled = false }: Props) {
  function toggle(id: number, checked: boolean) {
    const next = checked ? [...selected, id] : selected.filter((day) => day !== id);
    onChange([...new Set(next)].sort((a, b) => a - b));
  }

  return (
    <div className="weekday-picker" role="group" aria-label="Dias de produção">
      {WEEKDAYS.map((day) => {
        const checked = selected.includes(day.id);
        return (
          <label key={day.id} className={checked ? "weekday-option is-selected" : "weekday-option"}>
            <input
              type="checkbox"
              checked={checked}
              disabled={disabled}
              aria-label={day.name}
              onChange={(event) => toggle(day.id, event.target.checked)}
            />
            <span aria-hidden="true">
              {checked ? <span className="weekday-mark">✓</span> : null}
              {day.short}
            </span>
          </label>
        );
      })}
    </div>
  );
}
