import { type ReactNode } from 'react';

export default function TechnicalAuditDetails(props: {
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="technical-details">
      <summary>{props.summary}</summary>
      <div className="technical-details-body">{props.children}</div>
    </details>
  );
}
