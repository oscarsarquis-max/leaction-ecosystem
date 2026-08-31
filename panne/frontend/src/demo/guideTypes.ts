export type DemoGuideCountMap = {
  produtos: number | null;
  produtos_ativos?: number | null;
  produtos_inativos?: number | null;
  ingredientes: number | null;
  receitas: number | null;
  planos: number | null;
  ordens: number | null;
  fornecedores: number | null;
  lotes: number | null;
  saldos: number | null;
  movimentos: number | null;
  entradas_fiscais: number | null;
  perfis_disponiveis: number | null;
};

export type DemoGuidePayload = {
  schema_version: number;
  content_version: string;
  title: string;
  source: "live" | "fallback";
  generated_at?: string;
  counts_available?: boolean;
  what_is: {
    purpose: string;
    flow: string;
    data_nature: string;
    shared: string;
    not_production: string;
  };
  scenario: {
    anchor_date_label: string;
    primary_organization: string;
    isolation_organization: string;
    establishment_hint: string;
    shift_hint: string;
    areas_with_data: string[];
  };
  profiles: Array<{
    id: string;
    label: string;
    purpose: string;
    areas: string;
    actions: string;
    limits: string;
  }>;
  roadmap: Array<{
    step: number;
    title: string;
    path: string;
    requires_session: boolean;
  }>;
  safe_actions: {
    consult: string[];
    mutates_shared: string[];
    shared_notice: string;
  };
  integrations: Array<{ name: string; state: string; detail?: string }>;
  limitations: string[];
  version: {
    label: string;
    environment: string;
    anchor_date_label?: string;
    api_version?: string;
    migration_head_human?: string;
    migration_head_detail?: string | null;
    demo_anchor_date?: string;
    published_hint?: string;
  };
  counts: {
    source: string;
    updated_at: string | null;
    note: string | null;
    organizations: Array<{
      slug: string;
      display_name: string;
      role: string;
      counts: DemoGuideCountMap;
    }>;
    totals: DemoGuideCountMap;
  };
};
