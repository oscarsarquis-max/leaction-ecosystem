import { ApiError, requestJson } from "../services/http";
import type { PublicProduct, PublicProductList } from "./types";

export async function fetchShowcase(): Promise<PublicProductList> {
  return requestJson<PublicProductList>("/api/v1/catalog/showcase");
}

export async function fetchCatalog(page = 1): Promise<PublicProductList> {
  return requestJson<PublicProductList>(`/api/v1/catalog/products?page=${page}&page_size=24`);
}

export async function fetchProduct(slug: string): Promise<PublicProduct> {
  return requestJson<PublicProduct>(`/api/v1/catalog/products/${encodeURIComponent(slug)}`);
}

export function catalogErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 404) {
    return "Este pão não está à venda no momento.";
  }
  if (error instanceof ApiError && error.status === 0) {
    return "Não foi possível carregar os pães agora.";
  }
  return "Não foi possível carregar os pães agora.";
}
