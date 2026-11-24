import { requestJson } from "../../services/http";

export const B2B_LEADS_API = "/api/v1/marketplace/public/leads";

export const B2B_CATEGORIES: Array<[string, string]> = [
  ["queijos", "Queijos"],
  ["frios", "Frios e charcutaria"],
  ["vinhos", "Vinhos"],
  ["cervejas", "Cervejas"],
  ["azeites", "Azeites"],
  ["manteigas", "Manteigas"],
  ["geleias", "Geleias e pastas"],
  ["cafe_cha", "Café e chá"],
  ["pratos", "Pratos e acompanhamentos"],
  ["outro", "Outro"],
];

export type PartnerLead = {
  name: string;
  brand: string;
  category: string;
  city: string;
  whatsapp: string;
  email: string;
  link: string;
  message: string;
  consent: boolean;
  /** Campo-isca contra robôs: fica escondido e deve ir vazio. */
  website: string;
};

export function submitPartnerLead(lead: PartnerLead): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(B2B_LEADS_API, {
    method: "POST",
    body: JSON.stringify({
      ...lead,
      name: lead.name.trim(),
      brand: lead.brand.trim(),
      city: lead.city.trim(),
      whatsapp: lead.whatsapp.trim(),
      email: lead.email.trim(),
      link: lead.link.trim(),
      message: lead.message.trim(),
    }),
  });
}

/** WhatsApp brasileiro com DDD: 10 ou 11 dígitos (aceita +55). */
export function validWhatsapp(raw: string): boolean {
  const digits = raw.replace(/\D/g, "").replace(/^55(?=\d{10,11}$)/, "");
  return digits.length === 10 || digits.length === 11;
}

export function validEmail(raw: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(raw.trim());
}
