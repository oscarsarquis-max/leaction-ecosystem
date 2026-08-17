import type {
  BusinessModel,
  CertificationStatus,
  EmployeeRange,
  OrganizationProfile,
  QualityStructure,
} from "@/api/orgProfileApi";

/** Profile fields that may appear in OI supporting_facts (direct 1:1 keys). */
export const ORG_PROFILE_FIELD_KEYS = [
  "trade_name",
  "legal_name",
  "summary",
  "industry",
  "business_model",
  "employee_range",
  "unit_count",
  "certification_status",
  "quality_structure",
] as const;

export type OrgProfileFieldKey = (typeof ORG_PROFILE_FIELD_KEYS)[number];

export const ORG_PROFILE_FIELD_LABELS: Record<OrgProfileFieldKey, string> = {
  trade_name: "Nome da organização",
  legal_name: "Razão social",
  summary: "Descrição da organização",
  industry: "Setor de atuação",
  business_model: "Modelo de negócio",
  employee_range: "Número de colaboradores",
  unit_count: "Número de unidades",
  certification_status: "Situação da certificação",
  quality_structure: "Estrutura responsável pela qualidade",
};

export function isOrgProfileFieldKey(value: string): value is OrgProfileFieldKey {
  return (ORG_PROFILE_FIELD_KEYS as readonly string[]).includes(value);
}

export const BUSINESS_MODEL_OPTIONS: { value: BusinessModel; label: string }[] = [
  { value: "", label: "Não informado" },
  { value: "b2b", label: "B2B (empresa para empresa)" },
  { value: "b2c", label: "B2C (empresa para consumidor)" },
  { value: "b2b2c", label: "B2B2C" },
  { value: "services", label: "Serviços" },
  { value: "manufacturing", label: "Manufatura" },
  { value: "mixed", label: "Misto" },
  { value: "other", label: "Outro" },
];

export const EMPLOYEE_RANGE_OPTIONS: { value: EmployeeRange; label: string }[] = [
  { value: "", label: "Não informado" },
  { value: "1-10", label: "1 a 10" },
  { value: "11-50", label: "11 a 50" },
  { value: "51-200", label: "51 a 200" },
  { value: "201-500", label: "201 a 500" },
  { value: "501-1000", label: "501 a 1.000" },
  { value: "1000+", label: "Mais de 1.000" },
];

export const CERTIFICATION_STATUS_OPTIONS: {
  value: CertificationStatus;
  label: string;
}[] = [
  { value: "unknown", label: "Não sei / não informado" },
  { value: "none", label: "Sem certificação" },
  { value: "in_progress", label: "Em andamento" },
  { value: "certified", label: "Certificada" },
  { value: "expired", label: "Expirada" },
  { value: "not_applicable", label: "Não se aplica" },
];

export const QUALITY_STRUCTURE_OPTIONS: {
  value: QualityStructure;
  label: string;
}[] = [
  { value: "unknown", label: "Não sei / não informado" },
  { value: "none", label: "Sem estrutura dedicada" },
  { value: "informal", label: "Informal" },
  { value: "formal_partial", label: "Formal parcial" },
  { value: "formal", label: "Formal" },
];

function optionLabel<T extends string>(
  options: { value: T; label: string }[],
  value: T,
): string {
  return options.find((o) => o.value === value)?.label ?? value;
}

export function formatProfileFieldDisplay(
  profile: OrganizationProfile,
  key: OrgProfileFieldKey,
): string {
  switch (key) {
    case "trade_name":
    case "legal_name":
    case "summary":
    case "industry":
      return profile[key].trim() || "Não informado";
    case "business_model":
      return profile.business_model
        ? optionLabel(BUSINESS_MODEL_OPTIONS, profile.business_model)
        : "Não informado";
    case "employee_range":
      return profile.employee_range
        ? optionLabel(EMPLOYEE_RANGE_OPTIONS, profile.employee_range)
        : "Não informado";
    case "unit_count":
      return profile.unit_count == null ? "Não informado" : String(profile.unit_count);
    case "certification_status":
      return optionLabel(CERTIFICATION_STATUS_OPTIONS, profile.certification_status);
    case "quality_structure":
      return optionLabel(QUALITY_STRUCTURE_OPTIONS, profile.quality_structure);
  }
}

export function collectMissingProfileFields(
  supportingFacts: readonly string[],
): Set<OrgProfileFieldKey> {
  const out = new Set<OrgProfileFieldKey>();
  for (const fact of supportingFacts) {
    if (isOrgProfileFieldKey(fact)) out.add(fact);
  }
  return out;
}
