import { useEffect, useMemo, useState } from "react";
import type { FlowEvidence } from "./resolve";
import { canReadFiscal } from "../session/fiscalAccess";
import { useOrganization } from "../session/OrganizationContext";

const EMPTY: FlowEvidence = {
  ingredientsTotal: null,
  recipesTotal: null,
  ordersTotal: null,
  inventoryItemsTotal: null,
  products: null,
  fiscal: null,
};

/** Contagens leves das APIs já existentes — falha silenciosa → null (não inventa estado). */
export function useFlowEvidence(): { evidence: FlowEvidence; loading: boolean } {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [evidence, setEvidence] = useState<FlowEvidence>(EMPTY);
  const [loading, setLoading] = useState(false);

  const canIngredients = hasPermission("ingredient.read");
  const canRecipes = hasPermission("recipe.read");
  const canOrders = hasPermission("production.order.read");
  const canInventory = hasPermission("inventory.read");
  const canProducts = hasPermission("product.read");
  const canFiscal = canReadFiscal(hasPermission);

  const flags = useMemo(
    () => ({ canIngredients, canRecipes, canOrders, canInventory, canProducts, canFiscal }),
    [canIngredients, canRecipes, canOrders, canInventory, canProducts, canFiscal],
  );

  useEffect(() => {
    if (!orgId) {
      setEvidence(EMPTY);
      return;
    }
    let alive = true;
    setLoading(true);
    setEvidence(EMPTY);

    const tasks: Promise<void>[] = [];

    if (flags.canIngredients) {
      tasks.push(
        api
          .listIngredients({ limit: "1", offset: "0" })
          .then((page) => {
            if (alive) setEvidence((prev) => ({ ...prev, ingredientsTotal: page.total }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }
    if (flags.canFiscal) {
      tasks.push(
        api
          .getFiscalSummary()
          .then((body) => {
            if (alive) setEvidence((prev) => ({ ...prev, fiscal: body.data }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }
    if (flags.canProducts) {
      tasks.push(
        api
          .productsSummary()
          .then((body) => {
            if (alive) setEvidence((prev) => ({ ...prev, products: body.data }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }
    if (flags.canRecipes) {
      tasks.push(
        api
          .listRecipes({ limit: "1", offset: "0" })
          .then((page) => {
            if (alive) setEvidence((prev) => ({ ...prev, recipesTotal: page.total }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }
    if (flags.canOrders) {
      tasks.push(
        api
          .listOrders({})
          .then((page) => {
            if (!alive) return;
            const total = Array.isArray(page?.items) ? page.items.length : null;
            setEvidence((prev) => ({ ...prev, ordersTotal: total }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }
    if (flags.canInventory) {
      tasks.push(
        api
          .listInventory("/inventory/balances")
          .then((body) => {
            if (alive) setEvidence((prev) => ({ ...prev, inventoryItemsTotal: body.items?.length ?? 0 }));
          })
          .catch(() => {
            /* evidência indisponível */
          }),
      );
    }

    void Promise.all(tasks).finally(() => {
      if (alive) setLoading(false);
    });

    return () => {
      alive = false;
    };
  }, [api, orgId, flags]);

  return { evidence, loading };
}
