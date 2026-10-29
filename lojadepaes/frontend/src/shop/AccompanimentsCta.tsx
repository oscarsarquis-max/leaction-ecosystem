import { useEffect, useState } from "react";
import { fetchAccompaniments } from "./accompanimentsApi";

export function AccompanimentsCta({ bakeDate }: { bakeDate?: string | null }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchAccompaniments()
      .then((data) => {
        if (!cancelled) {
          setVisible(data.enabled && data.items.length > 0);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setVisible(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!visible) {
    return null;
  }

  const href = bakeDate && /^\d{4}-\d{2}-\d{2}$/.test(bakeDate) ? `/acompanhar?fornada=${bakeDate}` : "/acompanhar";

  return (
    <aside className="acc-home-cta">
      <div>
        <p className="eyebrow">À mesa</p>
        <h3>Para acompanhar seu pão</h3>
        <p>Complementos escolhidos para a mesa — compra e entrega pelo Mercado Livre ou pela Amazon, em separado.</p>
      </div>
      <a className="text-button" href={href}>
        Ver a seleção
      </a>
    </aside>
  );
}
