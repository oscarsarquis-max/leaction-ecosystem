import { requestJson } from "../services/http";
import type { HouseFidelityStatus } from "./houseFidelity";

export function fetchHouseFidelity(demo?: string): Promise<HouseFidelityStatus> {
  const query = demo ? `?demo=${encodeURIComponent(demo)}` : "";
  return requestJson<HouseFidelityStatus>(`/api/v1/promotions/house-fidelity${query}`);
}

export function submitHouseFidelitySignup(
  name: string,
  email: string,
  cpf: string,
): Promise<HouseFidelityStatus> {
  return requestJson<HouseFidelityStatus>("/api/v1/promotions/house-fidelity/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, cpf }),
  });
}

export function submitHouseFidelityResume(email: string): Promise<HouseFidelityStatus> {
  return requestJson<HouseFidelityStatus>("/api/v1/promotions/house-fidelity/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export function verifyHouseFidelity(email: string, code: string): Promise<HouseFidelityStatus> {
  return requestJson<HouseFidelityStatus>("/api/v1/promotions/house-fidelity/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, code }),
  });
}

export function verifyHouseFidelityLink(token: string): Promise<HouseFidelityStatus> {
  return requestJson<HouseFidelityStatus>(
    `/api/v1/promotions/house-fidelity/verify-link?token=${encodeURIComponent(token)}`,
    { method: "POST" },
  );
}

export function logoutHouseFidelity(): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>("/api/v1/promotions/house-fidelity/logout", {
    method: "POST",
  });
}

export function fetchHouseFidelityMe(): Promise<HouseFidelityStatus> {
  return requestJson<HouseFidelityStatus>("/api/v1/promotions/house-fidelity/me");
}

export type FidelityReward = {
  product_id: string;
  variant_id: string;
  name: string;
  slug: string;
  presentation: string;
  original_cents: number;
  benefit_cents: number;
  due_cents: number;
};

export function fetchHouseFidelityRewards(): Promise<{
  items: FidelityReward[];
  gaps: { slug: string; name: string }[];
  campaign_active: boolean;
}> {
  return requestJson("/api/v1/promotions/house-fidelity/rewards");
}

export function redeemHouseFidelity(payload: {
  variant_id: string;
  requested_date: string;
  idempotency_key: string;
}): Promise<{ public_reference: string; access_token?: string; notice: string; total_cents: number }> {
  return requestJson("/api/v1/promotions/house-fidelity/redeem", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
