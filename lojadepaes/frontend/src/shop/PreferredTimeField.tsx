import { formatWindowLabel, parsePreferredTime, preferredTimeOutsideWindows } from "./calendarDays";
import type { CalendarDay } from "./calendarApi";

type Props = {
  value: string;
  onChange: (next: string) => void;
  modality: "pickup" | "delivery";
  windows?: CalendarDay["windows"];
};

export function PreferredTimeField({ value, onChange, modality, windows = [] }: Props) {
  const parsed = parsePreferredTime(value);
  const outside = preferredTimeOutsideWindows(parsed, windows);
  const label = modality === "delivery" ? "Horário preferido para receber" : "Horário preferido para retirar";
  const windowText = windows
    .map((item) => formatWindowLabel(item))
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="preferred-time">
      <label htmlFor="preferred-time">
        {label}
        <input
          id="preferred-time"
          type="time"
          value={parsed ?? ""}
          onChange={(event) => onChange(event.target.value)}
        />
      </label>
      <p className="preferred-time-status">{parsed ? `Horário solicitado: ${parsed}` : "Sem preferência"}</p>
      {parsed ? (
        <button type="button" className="text-button" onClick={() => onChange("")}>
          Limpar horário
        </button>
      ) : null}
      {windowText ? <p className="fornada-note">Janela operacional: {windowText}.</p> : null}
      {outside ? (
        <p className="tip" role="status">
          Esse horário está fora da janela operacional. A Loja pode avaliar um acordo; isso não confirma nem
          altera a janela.
        </p>
      ) : null}
      <p className="fornada-note">
        Informe o horário que seria melhor para você. A Loja avaliará a possibilidade e confirmará com você.
      </p>
    </div>
  );
}
