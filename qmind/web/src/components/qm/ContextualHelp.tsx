type Props = {
  title?: string;
  children: string;
  example?: string;
  term?: string;
};

/** Ajuda contextual / glossário curto (ex.: termos ISO). */
export function ContextualHelp({
  title = "Por que isso importa",
  children,
  example,
  term,
}: Props) {
  return (
    <aside className="help-callout" data-testid="contextual-help" aria-label={title}>
      <p className="help-callout__title">
        {term ? `O que é “${term}”` : title}
      </p>
      <p className="help-callout__body">{children}</p>
      {example ? (
        <p className="help-callout__example">
          <span className="help-callout__example-label">Exemplo: </span>
          {example}
        </p>
      ) : null}
    </aside>
  );
}
