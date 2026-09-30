import { useEffect, useState } from "react";
import { adminRequest } from "./api";

type IngredientRow = {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  surcharge_pending: boolean;
  assistant_role?: string;
  admin_note?: string | null;
  compatible_dough_ids: string[];
};

type DoughType = { id: string; name: string; creator_kind?: string | null; is_active?: boolean };

type Payload = {
  price_cents: number;
  weight_grams: number;
  ingredients: IngredientRow[];
};

export function CustomLoafPanel() {
  const [price, setPrice] = useState("7000");
  const [weight, setWeight] = useState("500");
  const [ingredients, setIngredients] = useState<IngredientRow[]>([]);
  const [doughs, setDoughs] = useState<DoughType[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([
      adminRequest<Payload>("/api/v1/admin/custom-loaf"),
      adminRequest<DoughType[]>("/api/v1/admin/dough-types"),
    ])
      .then(([loaf, types]) => {
        setPrice(String(loaf.price_cents));
        setWeight(String(loaf.weight_grams));
        setIngredients(loaf.ingredients);
        setDoughs(types);
      })
      .catch(() => setNotice("Não foi possível carregar o pão personalizado."));
  }, []);

  async function savePrice() {
    setNotice(null);
    await adminRequest("/api/v1/admin/custom-loaf", {
      method: "PUT",
      body: JSON.stringify({ price_cents: Number(price), weight_grams: Number(weight) }),
    });
    setNotice("Preço e peso passam a valer só para pedidos novos.");
  }

  async function saveIngredient(row: IngredientRow) {
    setNotice(null);
    await adminRequest(`/api/v1/admin/ingredients/${row.id}`, {
      method: "PUT",
      body: JSON.stringify({
        name: row.name,
        description: row.description,
        is_active: row.is_active,
        compatible_dough_ids: row.compatible_dough_ids,
      }),
    });
    setNotice("Ingrediente atualizado. Compatibilidade em branco continua pendente.");
  }

  return (
    <article className="agenda-card">
      <h2>Pão personalizado</h2>
      <p className="agenda-help">
        O preço padrão e o peso ficam aqui. Alterar o valor não muda pedidos já gravados. Farinha e inclusões não
        criam cobrança própria enquanto o adicional estiver pendente.
      </p>
      <label>
        Preço em centavos
        <input value={price} onChange={(event) => setPrice(event.target.value)} inputMode="numeric" />
      </label>
      <label>
        Peso em gramas
        <input value={weight} onChange={(event) => setWeight(event.target.value)} inputMode="numeric" />
      </label>
      <button type="button" className="primary" onClick={() => void savePrice()}>
        Salvar preço do pão personalizado
      </button>
      {ingredients.map((row) => (
        <div key={row.id}>
          <p className="agenda-help">
            {row.assistant_role === "flour" ? "Farinha do criador" : "Complemento do criador"}
          </p>
          {row.admin_note ? <p className="agenda-help">{row.admin_note}</p> : null}
          <label>
            Nome
            <input
              value={row.name}
              onChange={(event) =>
                setIngredients((current) =>
                  current.map((item) => (item.id === row.id ? { ...item, name: event.target.value } : item)),
                )
              }
            />
          </label>
          <label>
            Descrição
            <textarea
              value={row.description}
              maxLength={280}
              onChange={(event) =>
                setIngredients((current) =>
                  current.map((item) => (item.id === row.id ? { ...item, description: event.target.value } : item)),
                )
              }
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={row.is_active}
              onChange={(event) =>
                setIngredients((current) =>
                  current.map((item) => (item.id === row.id ? { ...item, is_active: event.target.checked } : item)),
                )
              }
            />
            Disponível
          </label>
          <fieldset>
            <legend>Preparos compatíveis</legend>
            {doughs.map((dough) => (
              <label key={dough.id}>
                <input
                  type="checkbox"
                  checked={row.compatible_dough_ids.includes(dough.id)}
                  onChange={(event) =>
                    setIngredients((current) =>
                      current.map((item) => {
                        if (item.id !== row.id) return item;
                        const compatible_dough_ids = event.target.checked
                          ? [...item.compatible_dough_ids, dough.id]
                          : item.compatible_dough_ids.filter((id) => id !== dough.id);
                        return { ...item, compatible_dough_ids };
                      }),
                    )
                  }
                />
                {dough.name}
                {dough.creator_kind === "retired_mass" ? " (histórico)" : ""}
              </label>
            ))}
          </fieldset>
          {row.surcharge_pending ? <p className="agenda-help">Adicional pendente. Não entra no preço do pão.</p> : null}
          <button type="button" onClick={() => void saveIngredient(row)}>
            Salvar {row.name}
          </button>
        </div>
      ))}
      {notice ? <p className="agenda-help">{notice}</p> : null}
    </article>
  );
}
