/** Situação do fornecedor (gênero masculino). */
export const SUPPLIER_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  inactive: "Inativo",
};

/** Situação do item comercial. */
export const SUPPLIER_ITEM_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  inactive: "Inativo",
};

export function supplierStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return SUPPLIER_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function supplierItemStatusLabel(status: string | null | undefined): string {
  if (!status) return "—";
  return SUPPLIER_ITEM_STATUS_LABEL[status] ?? "Situação ainda não catalogada";
}

export function supplierStatusTone(
  status: string | null | undefined,
): "sucesso" | "atencao" | "info" | "neutro" | "erro" {
  if (status === "active") return "sucesso";
  if (status === "inactive") return "neutro";
  return "info";
}

/** Origem humana do preço observado (sem jargão de API). */
export function priceSourceLabel(source: string | null | undefined): string {
  if (source == null || source.trim() === "") return "Origem não informada";
  const value = source.trim();
  if (value === "seed-demo") return "Cadastro de demonstração";
  if (value.startsWith("receipt:")) return "Recebimento";
  if (value === "nota") return "Nota / observação";
  return value;
}

export function activeItemsSummary(count: number): string {
  if (count <= 0) return "Nenhum item ativo";
  if (count === 1) return "1 item ativo";
  return `${count} itens ativos`;
}
