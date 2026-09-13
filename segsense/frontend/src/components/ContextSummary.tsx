import { type ReactNode } from 'react';

export default function ContextSummary(props: {
  title?: string;
  children: ReactNode;
}) {
  return (
    <section className="context-summary" aria-labelledby="context-summary-heading">
      <h2 id="context-summary-heading">{props.title ?? 'Contexto deste convite'}</h2>
      {props.children}
    </section>
  );
}
