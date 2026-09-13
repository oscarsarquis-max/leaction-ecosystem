import { type ReactNode } from 'react';

export type HumanStatusKind = 'info' | 'warning' | 'danger' | 'success' | 'loading';

export default function HumanStatus(props: {
  kind: HumanStatusKind;
  title: string;
  headingLevel?: 'h1' | 'h2';
  children?: ReactNode;
  live?: 'polite' | 'assertive';
}) {
  const live = props.live ?? (props.kind === 'danger' ? 'assertive' : 'polite');
  const Heading = props.headingLevel ?? 'h1';
  return (
    <section className={`human-status human-status--${props.kind}`} aria-live={live}>
      <p className="human-status-mark" aria-hidden="true">
        {props.kind === 'loading' ? '…' : props.kind === 'danger' ? '!' : 'i'}
      </p>
      <div>
        <Heading>{props.title}</Heading>
        {props.children}
      </div>
    </section>
  );
}
