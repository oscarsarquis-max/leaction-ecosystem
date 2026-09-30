import { useEffect, useState } from "react";
import { formatCents } from "../lib/money";
import type { CalendarLine } from "./calendarApi";
import { fetchSuggestions, type SuggestionItem, type SuggestionsPayload } from "./suggestionsApi";

type Props = {
  selectedDate: string | null;
  lines: CalendarLine[];
};

function priceLabel(item: SuggestionItem): string {
  if (item.price.cents === null) {
    return "Preço a definir";
  }
  const formatted = formatCents(item.price.cents);
  return item.price_is_from ? `A partir de ${formatted}` : formatted;
}

export function FornadaPanel({ selectedDate, lines }: Props) {
  const [data, setData] = useState<SuggestionsPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [suggestionsAttempt, setSuggestionsAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetchSuggestions({ selected: selectedDate, lines })
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setError("Não foi possível carregar as sugestões agora.");
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
  }, [lines, selectedDate, suggestionsAttempt]);

  return (
    <aside className="fornada-panel" aria-labelledby="fornada-panel-title">
      <h3 id="fornada-panel-title">{data?.title ?? "Vagas nesta fornada"}</h3>
      {loading ? <p className="fornada-note">Consultando as vagas desta fornada…</p> : null}
      {error ? (
        <p className="fornada-note" role="alert">
          {error}{" "}
          <button type="button" className="text-button" onClick={() => setSuggestionsAttempt((current) => current + 1)}>
            Tentar as sugestões de novo
          </button>
        </p>
      ) : null}
      {!loading && !error && data?.message ? <p className="fornada-note">{data.message}</p> : null}
      {!loading && !error && data && data.items.length > 0 ? (
        <ul className="fornada-suggestions">
          {data.items.map((item) => (
            <li key={item.slug}>
              <article className="fornada-card">
                {item.image_url ? (
                  <img src={item.image_url} alt={item.image_alt || item.name} />
                ) : (
                  <div className="fornada-card-missing">Sem foto</div>
                )}
                <div>
                  <h4>{item.name}</h4>
                  <p>
                    {item.presentation} · {priceLabel(item)}
                  </p>
                  <a className="text-button" href={item.href}>
                    Escolher este pão
                  </a>
                </div>
              </article>
            </li>
          ))}
        </ul>
      ) : null}
    </aside>
  );
}
