const PLACEHOLDER = /\{\{([a-z][a-zA-Z0-9]{1,39})\}\}/g;

export type MaterializedSummary =
  | { mode: 'materialized'; text: string }
  | { mode: 'split' };

function hasPublisherValue(value: unknown): boolean {
  if (value === undefined || value === null) {
    return false;
  }
  if (typeof value === 'string') {
    return value.length > 0;
  }
  return true;
}

export function materializeContextSummary(
  template: string,
  publisherValues: Record<string, unknown>,
): MaterializedSummary {
  const keys = [...template.matchAll(PLACEHOLDER)].map((match) => match[1]);
  if (keys.some((key) => key === undefined || !hasPublisherValue(publisherValues[key]))) {
    return { mode: 'split' };
  }
  const text = template.replace(PLACEHOLDER, (_full, key: string) =>
    String(publisherValues[key]),
  );
  return { mode: 'materialized', text };
}
