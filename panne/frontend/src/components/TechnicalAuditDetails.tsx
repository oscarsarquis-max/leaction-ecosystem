import type { ReactNode } from "react";

export type TechnicalDetailRow = {
  label: string;
  value: string;
  copyable?: boolean;
};

type Props = {
  title?: string;
  purpose?: string;
  rows: TechnicalDetailRow[];
  children?: ReactNode;
};

/**
 * Divulgação progressiva de detalhes de auditoria (R026-004).
 * Recolhido por padrão; acionável por teclado via &lt;details&gt;.
 */
export function TechnicalAuditDetails({
  title = "Detalhes técnicos de auditoria",
  purpose = "Informações para suporte, auditoria ou integração. Não são necessárias no dia a dia.",
  rows,
  children,
}: Props) {
  const usable = rows.filter((row) => row.value && row.value !== "—");
  if (usable.length === 0 && !children) return null;

  return (
    <details className="technical-audit">
      <summary>{title}</summary>
      <p className="meta">{purpose}</p>
      {usable.length > 0 ? (
        <dl className="technical-audit-list">
          {usable.map((row) => (
            <div key={row.label} className="technical-audit-row">
              <dt>{row.label}</dt>
              <dd>
                <code className="technical-audit-value">{row.value}</code>
                {row.copyable ? (
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => {
                      void navigator.clipboard?.writeText(row.value);
                    }}
                  >
                    Copiar
                  </button>
                ) : null}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {children}
    </details>
  );
}
