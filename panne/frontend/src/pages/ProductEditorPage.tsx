import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { isCancelledError } from "../api/errors";
import type { CatalogItem, ProductFamilyRow } from "../api/types";
import { ErrorState, LoadingState } from "../components/Feedback";
import {
  isSupplyModeInPreparation,
  productSupplyModeLabel,
  SUPPLY_MODE_PREPARATION_NOTE,
} from "../language/products";
import { useCommand } from "../ops/useCommand";
import { useOrganization } from "../session/OrganizationContext";

type FormState = {
  code: string;
  display_name: string;
  description: string;
  purpose: string;
  supply_mode: string;
  family_id: string;
  stock_unit_id: string;
  sale_unit_id: string;
  net_content: string;
  net_content_unit_id: string;
  default_shelf_life_days: string;
  packaging_description: string;
};

const EMPTY_FORM: FormState = {
  code: "",
  display_name: "",
  description: "",
  purpose: "final",
  supply_mode: "produced",
  family_id: "",
  stock_unit_id: "",
  sale_unit_id: "",
  net_content: "",
  net_content_unit_id: "",
  default_shelf_life_days: "",
  packaging_description: "",
};

const SUPPLY_MODES = ["produced", "purchased", "mixed", "combo"];

function unitOptionLabel(unit: CatalogItem): string {
  return unit.name ?? unit.code ?? "Unidade";
}

export function ProductEditorPage() {
  const { productId } = useParams();
  const isNew = !productId;
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const navigate = useNavigate();
  const command = useCommand();

  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [rowVersion, setRowVersion] = useState<number | null>(null);
  const [units, setUnits] = useState<CatalogItem[]>([]);
  const [families, setFamilies] = useState<ProductFamilyRow[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [error, setError] = useState<unknown>(null);

  function change<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  useEffect(() => {
    if (!orgId) return;
    let alive = true;
    void Promise.all([api.getCatalogUnits(), api.listProductFamilies()])
      .then(([unitPage, familyPage]) => {
        if (!alive) return;
        setUnits(unitPage.data);
        setFamilies(familyPage.items);
      })
      .catch((caught) => {
        if (isCancelledError(caught)) return;
      });
    return () => {
      alive = false;
    };
  }, [api, orgId]);

  useEffect(() => {
    if (!productId || !orgId) {
      setForm(EMPTY_FORM);
      setRowVersion(null);
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(null);
    api
      .getProduct(productId)
      .then((envelope) => {
        if (!alive) return;
        const product = envelope.data;
        setForm({
          code: product.code,
          display_name: product.display_name,
          description: product.description ?? "",
          purpose: product.purpose,
          supply_mode: product.supply_mode,
          family_id: product.family?.id ?? "",
          stock_unit_id: product.stock_unit?.id ?? "",
          sale_unit_id: product.sale_unit?.id ?? "",
          net_content: product.net_content ?? "",
          net_content_unit_id: product.net_content_unit?.id ?? "",
          default_shelf_life_days:
            product.default_shelf_life_days == null ? "" : String(product.default_shelf_life_days),
          packaging_description: product.packaging_description ?? "",
        });
        setRowVersion(product.row_version);
        setLoading(false);
      })
      .catch((caught) => {
        if (!alive || isCancelledError(caught)) return;
        setError(caught);
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [api, productId, orgId]);

  function buildBody(): Record<string, unknown> {
    return {
      code: form.code.trim(),
      display_name: form.display_name.trim(),
      description: form.description.trim() || null,
      purpose: form.purpose,
      supply_mode: form.supply_mode,
      family_id: form.family_id || null,
      stock_unit_id: form.stock_unit_id || null,
      sale_unit_id: form.sale_unit_id || null,
      net_content: form.net_content.trim() || null,
      net_content_unit_id: form.net_content_unit_id || null,
      default_shelf_life_days: form.default_shelf_life_days.trim()
        ? Number(form.default_shelf_life_days)
        : null,
      packaging_description: form.packaging_description.trim() || null,
    };
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (command.pending) return;
    if (!form.code.trim() || !form.display_name.trim()) return;
    try {
      if (isNew) {
        const created = await command.run(`product:${form.code.trim()}`, (key) =>
          api.createProduct(buildBody(), key),
        );
        if (created?.data.id) navigate(`/produtos/${created.data.id}`);
        return;
      }
      await command.run(`product-edit:${productId}`, (key) =>
        api.patchProduct(productId as string, buildBody(), {
          idempotencyKey: key,
          rowVersion,
        }),
      );
      navigate(`/produtos/${productId}`);
    } catch {
      /* erro apresentado em command.error */
    }
  }

  const canSave = isNew ? hasPermission("product.create") : hasPermission("product.update");

  if (loading) return <LoadingState />;
  if (!isNew && error) return <ErrorState error={error} />;

  return (
    <div className="stage">
      <div>
        <div className="page-head">
          <div>
            <h1>{isNew ? "Novo produto" : `Editar ${form.display_name || "produto"}`}</h1>
          </div>
        </div>
        <p className="lede">
          O produto vale por si. Receita, estoque e rotulagem se conectam depois, quando a operação
          precisar.
        </p>

        <form className="panel" onSubmit={onSubmit}>
          <h2>Identidade</h2>
          <label>
            Código (obrigatório)
            <input
              value={form.code}
              onChange={(event) => change("code", event.target.value)}
              required
              autoComplete="off"
              disabled={command.pending}
            />
          </label>
          <label>
            Nome (obrigatório)
            <input
              value={form.display_name}
              onChange={(event) => change("display_name", event.target.value)}
              required
              autoComplete="off"
              disabled={command.pending}
            />
          </label>
          <label>
            Descrição
            <textarea
              value={form.description}
              onChange={(event) => change("description", event.target.value)}
              disabled={command.pending}
            />
          </label>
          <label>
            Finalidade
            <select
              value={form.purpose}
              onChange={(event) => change("purpose", event.target.value)}
              disabled={command.pending}
            >
              <option value="final">Produto final</option>
              <option value="intermediate">Preparo intermediário</option>
            </select>
          </label>
          <label>
            Abastecimento
            <select
              value={form.supply_mode}
              onChange={(event) => change("supply_mode", event.target.value)}
              disabled={command.pending}
            >
              {SUPPLY_MODES.map((mode) => (
                <option
                  key={mode}
                  value={mode}
                  disabled={isSupplyModeInPreparation(mode) && form.supply_mode !== mode}
                >
                  {productSupplyModeLabel(mode)}
                </option>
              ))}
            </select>
          </label>
          {isSupplyModeInPreparation(form.supply_mode) ? (
            <p className="meta" role="status">
              {SUPPLY_MODE_PREPARATION_NOTE}
            </p>
          ) : null}
          <label>
            Família
            <select
              value={form.family_id}
              onChange={(event) => change("family_id", event.target.value)}
              disabled={command.pending}
            >
              <option value="">Sem família</option>
              {families.map((family) => (
                <option key={family.id} value={family.id}>
                  {family.display_name}
                </option>
              ))}
            </select>
          </label>

          <h2>Embalagem e medida</h2>
          <label>
            Unidade de estoque
            <select
              value={form.stock_unit_id}
              onChange={(event) => change("stock_unit_id", event.target.value)}
              disabled={command.pending}
            >
              <option value="">Não informada</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unitOptionLabel(unit)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Unidade de venda
            <select
              value={form.sale_unit_id}
              onChange={(event) => change("sale_unit_id", event.target.value)}
              disabled={command.pending}
            >
              <option value="">Não informada</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unitOptionLabel(unit)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Conteúdo líquido
            <input
              value={form.net_content}
              inputMode="decimal"
              onChange={(event) => change("net_content", event.target.value)}
              disabled={command.pending}
            />
          </label>
          <label>
            Unidade do conteúdo
            <select
              value={form.net_content_unit_id}
              onChange={(event) => change("net_content_unit_id", event.target.value)}
              disabled={command.pending}
            >
              <option value="">Não informada</option>
              {units.map((unit) => (
                <option key={unit.id} value={unit.id}>
                  {unitOptionLabel(unit)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Validade padrão em dias
            <input
              value={form.default_shelf_life_days}
              inputMode="numeric"
              onChange={(event) => change("default_shelf_life_days", event.target.value)}
              disabled={command.pending}
            />
          </label>
          <label>
            Embalagem
            <input
              value={form.packaging_description}
              onChange={(event) => change("packaging_description", event.target.value)}
              disabled={command.pending}
            />
          </label>

          {command.error ? (
            <p className="error" role="alert">
              {command.error.message || "Não foi possível guardar o produto."}
            </p>
          ) : null}
          {canSave ? (
            <button type="submit" className="primary" disabled={command.pending}>
              {command.pending ? "A guardar…" : isNew ? "Criar produto" : "Guardar produto"}
            </button>
          ) : (
            <p className="meta">Edição oculta neste papel.</p>
          )}
        </form>

        <p>
          <Link className="ghost" to={isNew ? "/produtos" : `/produtos/${productId}`}>
            {isNew ? "Voltar aos produtos" : "Voltar ao produto"}
          </Link>
        </p>
      </div>
      <aside className="panel">
        <h2>Sem receita também vale</h2>
        <p>
          Produto comprado pronto não precisa de receita. Produto produzido pode nascer sem receita:
          o cadastro fica válido e a produção só é liberada quando houver receita vigente.
        </p>
        <p className="meta">
          Nada aqui publica preço, rótulo ou ordem de produção. São passos separados do fluxo.
        </p>
      </aside>
    </div>
  );
}
