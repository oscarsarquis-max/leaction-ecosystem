import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { useOrgProfile, usePatchOrgProfile } from "@/hooks/useOrgProfile";
import { useLatestOrganizationalIntelligence } from "@/hooks/useOrganizationalIntelligence";
import { LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { canEditOrganizationProfile } from "@/lib/permissions";
import {
  BUSINESS_MODEL_OPTIONS,
  CERTIFICATION_STATUS_OPTIONS,
  EMPLOYEE_RANGE_OPTIONS,
  ORG_PROFILE_FIELD_KEYS,
  ORG_PROFILE_FIELD_LABELS,
  QUALITY_STRUCTURE_OPTIONS,
  collectMissingProfileFields,
  formatProfileFieldDisplay,
  type OrgProfileFieldKey,
} from "@/lib/orgProfileLabels";
import type {
  BusinessModel,
  CertificationStatus,
  EmployeeRange,
  OrganizationProfile,
  OrganizationProfilePatch,
  QualityStructure,
} from "@/api/orgProfileApi";

type Props = {
  onProfileSaved?: () => void;
};

type FormState = {
  trade_name: string;
  legal_name: string;
  summary: string;
  industry: string;
  business_model: BusinessModel;
  employee_range: EmployeeRange;
  unit_count: string;
  certification_status: CertificationStatus;
  quality_structure: QualityStructure;
};

function toForm(profile: OrganizationProfile): FormState {
  return {
    trade_name: profile.trade_name,
    legal_name: profile.legal_name,
    summary: profile.summary,
    industry: profile.industry,
    business_model: profile.business_model,
    employee_range: profile.employee_range,
    unit_count: profile.unit_count == null ? "" : String(profile.unit_count),
    certification_status: profile.certification_status,
    quality_structure: profile.quality_structure,
  };
}

function toPatch(form: FormState): OrganizationProfilePatch {
  const trimmedUnits = form.unit_count.trim();
  let unit_count: number | null = null;
  if (trimmedUnits !== "") {
    const n = Number(trimmedUnits);
    unit_count = Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
  }
  return {
    trade_name: form.trade_name,
    legal_name: form.legal_name,
    summary: form.summary,
    industry: form.industry,
    business_model: form.business_model,
    employee_range: form.employee_range,
    unit_count,
    certification_status: form.certification_status,
    quality_structure: form.quality_structure,
  };
}

function FieldShell({
  fieldKey,
  highlighted,
  children,
}: {
  fieldKey: OrgProfileFieldKey;
  highlighted: boolean;
  children: ReactNode;
}) {
  return (
    <label
      className={`block text-sm ${
        highlighted
          ? "rounded-md border border-[var(--qm-attention)] bg-[var(--qm-surface)] p-2"
          : ""
      }`}
      data-testid={`org-context-field-${fieldKey}`}
      data-needed={highlighted ? "true" : "false"}
    >
      <span className="font-medium text-[var(--qm-ink)]">
        {ORG_PROFILE_FIELD_LABELS[fieldKey]}
      </span>
      {highlighted ? (
        <span
          className="ml-2 text-xs font-semibold text-[var(--qm-attention)]"
          data-testid={`org-context-needed-${fieldKey}`}
        >
          Informação necessária
        </span>
      ) : null}
      <div className="mt-1">{children}</div>
    </label>
  );
}

export function OrgOrganizationContext({ onProfileSaved }: Props) {
  const org = useOrganization();
  const canEdit = canEditOrganizationProfile(org.currentOrganization?.roles);
  const profileQuery = useOrgProfile();
  const patch = usePatchOrgProfile();
  const latestOi = useLatestOrganizationalIntelligence();

  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<FormState | null>(null);
  const [savedHint, setSavedHint] = useState(false);

  const missingKeys = useMemo(() => {
    const facts =
      latestOi.data?.insights.insights.flatMap(
        (i) => i.explanation?.supporting_facts ?? [],
      ) ?? [];
    return collectMissingProfileFields(facts);
  }, [latestOi.data]);

  useEffect(() => {
    setEditing(false);
    setForm(null);
    setSavedHint(false);
  }, [org.currentOrganizationId]);

  if (profileQuery.isLoading) {
    return <LoadingPanel title="Carregando contexto da organização…" />;
  }

  if (profileQuery.isError) {
    return (
      <ApiErrorBanner
        title="Não foi possível carregar o contexto da organização"
        error={profileQuery.error}
        onRetry={() => void profileQuery.refetch()}
      />
    );
  }

  const profile = profileQuery.data;
  if (!profile) {
    return null;
  }

  const startEdit = () => {
    setForm(toForm(profile));
    setEditing(true);
    setSavedHint(false);
    patch.reset();
  };

  const cancelEdit = () => {
    setEditing(false);
    setForm(null);
    patch.reset();
  };

  const save = () => {
    if (!form) return;
    patch.mutate(toPatch(form), {
      onSuccess: () => {
        setEditing(false);
        setForm(null);
        setSavedHint(true);
        onProfileSaved?.();
      },
    });
  };

  const summaryKeys: OrgProfileFieldKey[] = [
    "trade_name",
    "industry",
    "employee_range",
    "certification_status",
    "quality_structure",
  ];

  return (
    <section
      className="space-y-4 rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface)] p-4"
      data-testid="org-organization-context"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="font-display text-lg text-[var(--qm-ink)]">
            Contexto da Organização
          </h2>
          <p className="mt-1 text-sm text-[var(--qm-muted)]">
            Fatos organizacionais que alimentam a Inteligência Organizacional.
            Completar o contexto melhora a análise de prontidão.
          </p>
        </div>
        {canEdit && !editing ? (
          <button
            type="button"
            className="qm-btn-secondary shrink-0"
            data-testid="org-context-edit"
            onClick={startEdit}
          >
            Editar contexto
          </button>
        ) : null}
      </div>

      {savedHint ? (
        <p
          className="text-sm font-medium text-[var(--qm-success)]"
          data-testid="org-context-saved"
        >
          Contexto salvo.
        </p>
      ) : null}

      {patch.isError ? (
        <ApiErrorBanner
          title="Não foi possível salvar o contexto"
          error={patch.error}
          onRetry={save}
        />
      ) : null}

      {!editing ? (
        <dl
          className="grid gap-3 sm:grid-cols-2"
          data-testid="org-context-summary"
        >
          {summaryKeys.map((key) => (
            <div key={key}>
              <dt className="text-xs font-semibold uppercase tracking-wide text-[var(--qm-muted)]">
                {ORG_PROFILE_FIELD_LABELS[key]}
              </dt>
              <dd
                className="mt-0.5 text-sm text-[var(--qm-ink)]"
                data-testid={`org-context-summary-${key}`}
              >
                {formatProfileFieldDisplay(profile, key)}
              </dd>
            </div>
          ))}
        </dl>
      ) : form ? (
        <form
          className="grid gap-3 sm:grid-cols-2"
          data-testid="org-context-form"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          {ORG_PROFILE_FIELD_KEYS.map((key) => {
            const highlighted = missingKeys.has(key);
            if (key === "summary") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <textarea
                    className="qm-field min-h-[88px] w-full"
                    value={form.summary}
                    onChange={(e) =>
                      setForm({ ...form, summary: e.target.value })
                    }
                  />
                </FieldShell>
              );
            }
            if (key === "business_model") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <select
                    className="qm-field w-full"
                    value={form.business_model}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        business_model: e.target.value as BusinessModel,
                      })
                    }
                  >
                    {BUSINESS_MODEL_OPTIONS.map((o) => (
                      <option key={o.value || "empty"} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </FieldShell>
              );
            }
            if (key === "employee_range") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <select
                    className="qm-field w-full"
                    value={form.employee_range}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        employee_range: e.target.value as EmployeeRange,
                      })
                    }
                  >
                    {EMPLOYEE_RANGE_OPTIONS.map((o) => (
                      <option key={o.value || "empty"} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </FieldShell>
              );
            }
            if (key === "certification_status") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <select
                    className="qm-field w-full"
                    value={form.certification_status}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        certification_status: e.target
                          .value as CertificationStatus,
                      })
                    }
                  >
                    {CERTIFICATION_STATUS_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </FieldShell>
              );
            }
            if (key === "quality_structure") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <select
                    className="qm-field w-full"
                    value={form.quality_structure}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        quality_structure: e.target.value as QualityStructure,
                      })
                    }
                  >
                    {QUALITY_STRUCTURE_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </FieldShell>
              );
            }
            if (key === "unit_count") {
              return (
                <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                  <input
                    type="number"
                    min={0}
                    className="qm-field w-full"
                    value={form.unit_count}
                    onChange={(e) =>
                      setForm({ ...form, unit_count: e.target.value })
                    }
                  />
                </FieldShell>
              );
            }
            return (
              <FieldShell key={key} fieldKey={key} highlighted={highlighted}>
                <input
                  className="qm-field w-full"
                  value={form[key]}
                  onChange={(e) =>
                    setForm({ ...form, [key]: e.target.value })
                  }
                />
              </FieldShell>
            );
          })}

          <div className="flex flex-wrap gap-2 sm:col-span-2">
            <button
              type="submit"
              className="qm-btn-primary"
              data-testid="org-context-save"
              disabled={patch.isPending}
            >
              {patch.isPending ? "Salvando…" : "Salvar contexto"}
            </button>
            <button
              type="button"
              className="qm-btn-secondary"
              data-testid="org-context-cancel"
              disabled={patch.isPending}
              onClick={cancelEdit}
            >
              Cancelar
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
