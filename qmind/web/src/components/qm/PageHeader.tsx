import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: string;
  explanation: string;
  expectedResult?: string;
  progress?: string;
  nextStep?: string;
  actions?: ReactNode;
  children?: ReactNode;
};

/** Cabeçalho padrão: onde estou / o que fazer / por quê / próximo passo. */
export function PageHeader({
  eyebrow,
  title,
  explanation,
  expectedResult,
  progress,
  nextStep,
  actions,
  children,
}: Props) {
  return (
    <header className="qm-page-header" data-testid="page-header">
      <div className="qm-page-header__main">
        {eyebrow ? <p className="qm-page-header__eyebrow">{eyebrow}</p> : null}
        <h1 className="qm-page-header__title">{title}</h1>
        <p className="qm-page-header__explain">{explanation}</p>
        {(expectedResult || progress || nextStep) && (
          <div className="qm-page-header__meta">
            {expectedResult ? (
              <p>
                <span className="qm-meta-label">Resultado esperado</span>
                {expectedResult}
              </p>
            ) : null}
            {progress ? (
              <p>
                <span className="qm-meta-label">Progresso</span>
                {progress}
              </p>
            ) : null}
            {nextStep ? (
              <p>
                <span className="qm-meta-label">Próxima etapa</span>
                {nextStep}
              </p>
            ) : null}
          </div>
        )}
        {children}
      </div>
      {actions ? <div className="qm-page-header__actions">{actions}</div> : null}
    </header>
  );
}
