import type { ReactNode } from "react";
import type { GuidedContext, GuidedStep } from "@/api/guidedTypes";
import { ContextualHelp } from "@/components/qm";

type Props = {
  step: GuidedStep;
  context: GuidedContext;
  onChange: (next: GuidedContext) => void;
  readOnly?: boolean;
};

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold text-[var(--qm-ink)]">{label}</span>
      {hint ? <span className="block text-sm text-[var(--qm-muted)]">{hint}</span> : null}
      {children}
    </label>
  );
}

function ListEditor({
  items,
  fields,
  onChange,
  addLabel,
  readOnly,
}: {
  items: Record<string, string>[];
  fields: { key: string; label: string; placeholder?: string }[];
  onChange: (next: Record<string, string>[]) => void;
  addLabel: string;
  readOnly?: boolean;
}) {
  return (
    <div className="space-y-4">
      {items.length === 0 ? (
        <p className="rounded-md border border-dashed border-[var(--qm-line-strong)] bg-[var(--qm-surface-soft)] px-3 py-3 text-sm text-[var(--qm-muted)]">
          Ainda vazio — use o botão abaixo para adicionar o primeiro item. Você pode
          voltar e editar depois; o salvamento é automático.
        </p>
      ) : null}
      {items.map((item, idx) => (
        <div
          key={idx}
          className="space-y-3 border-b border-[var(--qm-line)] pb-4 last:border-0"
        >
          {fields.map((f) => (
            <Field key={f.key} label={f.label}>
              <input
                className="qm-field"
                value={item[f.key] ?? ""}
                placeholder={f.placeholder}
                disabled={readOnly}
                onChange={(e) => {
                  const next = items.map((row, i) =>
                    i === idx ? { ...row, [f.key]: e.target.value } : row,
                  );
                  onChange(next);
                }}
              />
            </Field>
          ))}
          {!readOnly ? (
            <button
              type="button"
              className="text-sm font-semibold text-[var(--qm-muted)] hover:text-[var(--qm-ink)]"
              onClick={() => onChange(items.filter((_, i) => i !== idx))}
            >
              Remover
            </button>
          ) : null}
        </div>
      ))}
      {!readOnly ? (
        <button
          type="button"
          className="qm-btn-secondary"
          onClick={() => {
            const blank: Record<string, string> = {};
            for (const f of fields) blank[f.key] = "";
            onChange([...items, blank]);
          }}
        >
          {addLabel}
        </button>
      ) : null}
    </div>
  );
}

export function GuidedContextSteps({ step, context, onChange, readOnly }: Props) {
  if (step === "organization") {
    const p = context.organization_profile;
    return (
      <div className="space-y-5">
        <ContextualHelp
          title="Por que começamos aqui"
          example="“Metalúrgica Horizonte — usinagem sob encomenda para o setor automotivo, cerca de 45 pessoas.”"
        >
          Antes de perguntas da norma, precisamos saber quem é a organização. Responda
          como explicaria a um consultor na primeira reunião.
        </ContextualHelp>
        <Field
          label="Nome da organização"
          hint="Como a empresa é conhecida no dia a dia."
        >
          <input
            className="qm-field"
            value={p.trade_name}
            placeholder="Ex.: Metalúrgica Horizonte"
            disabled={readOnly}
            onChange={(e) =>
              onChange({
                ...context,
                organization_profile: { ...p, trade_name: e.target.value },
              })
            }
          />
        </Field>
        <Field
          label="O que a empresa faz"
          hint="Em poucas frases: produtos, serviços e clientes típicos."
        >
          <textarea
            className="qm-field min-h-28"
            value={p.summary}
            placeholder="Ex.: Produz peças usinadas sob encomenda para montadoras e fornecedores Tier-2."
            disabled={readOnly}
            onChange={(e) =>
              onChange({
                ...context,
                organization_profile: { ...p, summary: e.target.value },
              })
            }
          />
        </Field>
        <Field label="Porte aproximado" hint="Ex.: até 20 pessoas; 20–100; acima de 100.">
          <input
            className="qm-field"
            value={p.size_band}
            placeholder="Ex.: 20–100 pessoas"
            disabled={readOnly}
            onChange={(e) =>
              onChange({
                ...context,
                organization_profile: { ...p, size_band: e.target.value },
              })
            }
          />
        </Field>
      </div>
    );
  }

  if (step === "qms_scope") {
    const s = context.qms_scope;
    return (
      <div className="space-y-5">
        <ContextualHelp
          term="escopo"
          example="“Fabricação e expedição de peças usinadas na planta de Campinas; exclusão: desenvolvimento de produto (feito pelo cliente).”"
        >
          Escopo é o limite do que esta avaliação cobre — atividades, produtos e locais.
          Não precisa usar termos da norma; descreva o que entra e o que fica de fora.
        </ContextualHelp>
        <Field
          label="O que esta avaliação cobre"
          hint="Produtos, serviços, unidades e atividades incluídos."
        >
          <textarea
            className="qm-field min-h-28"
            value={s.description}
            placeholder="Ex.: Produção e expedição na planta de Campinas."
            disabled={readOnly}
            onChange={(e) =>
              onChange({
                ...context,
                qms_scope: { ...s, description: e.target.value },
              })
            }
          />
        </Field>
        <Field label="O que fica de fora (se houver)">
          <textarea
            className="qm-field min-h-20"
            value={s.exclusions}
            disabled={readOnly}
            onChange={(e) => {
              const exclusions = e.target.value;
              onChange({
                ...context,
                qms_scope: {
                  ...s,
                  exclusions,
                  // Sem exclusões, a justificativa some da entrevista (valor antigo permanece salvo).
                  exclusion_justification: exclusions.trim()
                    ? s.exclusion_justification
                    : s.exclusion_justification,
                },
              });
            }}
          />
        </Field>
        {s.exclusions.trim() ? (
          <Field
            label="Por que fica de fora"
            hint="Explique o motivo de forma objetiva — sem jargão. Só pedimos isso quando há exclusões."
          >
            <textarea
              className="qm-field min-h-20"
              value={s.exclusion_justification}
              disabled={readOnly}
              data-testid="exclusion-justification"
              onChange={(e) =>
                onChange({
                  ...context,
                  qms_scope: { ...s, exclusion_justification: e.target.value },
                })
              }
            />
          </Field>
        ) : null}
      </div>
    );
  }

  if (step === "products_services") {
    return (
      <ListEditor
        readOnly={readOnly}
        addLabel="Adicionar produto ou serviço"
        items={context.products_services}
        fields={[
          { key: "name", label: "Nome", placeholder: "Ex.: Usinagem sob encomenda" },
          { key: "notes", label: "Observações", placeholder: "Clientes, volumes, particularidades" },
        ]}
        onChange={(next) =>
          onChange({
            ...context,
            products_services: next as GuidedContext["products_services"],
          })
        }
      />
    );
  }

  if (step === "sites") {
    return (
      <ListEditor
        readOnly={readOnly}
        addLabel="Adicionar unidade ou local"
        items={context.sites}
        fields={[
          { key: "name", label: "Unidade", placeholder: "Ex.: Planta São Paulo" },
          { key: "location", label: "Local", placeholder: "Cidade / endereço resumido" },
          { key: "notes", label: "Observações" },
        ]}
        onChange={(next) =>
          onChange({ ...context, sites: next as GuidedContext["sites"] })
        }
      />
    );
  }

  if (step === "processes") {
    return (
      <ListEditor
        readOnly={readOnly}
        addLabel="Adicionar processo"
        items={context.processes}
        fields={[
          { key: "name", label: "Processo", placeholder: "Ex.: Comercial → Produção → Expedição" },
          { key: "owner", label: "Responsável", placeholder: "Nome ou função" },
          { key: "notes", label: "Observações" },
        ]}
        onChange={(next) =>
          onChange({
            ...context,
            processes: next as GuidedContext["processes"],
          })
        }
      />
    );
  }

  if (step === "stakeholders") {
    return (
      <ListEditor
        readOnly={readOnly}
        addLabel="Adicionar parte interessada"
        items={context.stakeholders}
        fields={[
          { key: "name", label: "Parte interessada", placeholder: "Ex.: Clientes industriais" },
          { key: "interest", label: "O que espera da qualidade", placeholder: "Ex.: prazo e conformidade" },
          { key: "notes", label: "Observações" },
        ]}
        onChange={(next) =>
          onChange({
            ...context,
            stakeholders: next as GuidedContext["stakeholders"],
          })
        }
      />
    );
  }

  return null;
}
