export function FinancialSummary({
  items,
}: {
  items: { label: string; value: string; hint?: string }[];
}) {
  return (
    <div className="financial-summary" aria-live="polite">
      {items.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          {item.hint ? <span>{item.hint}</span> : null}
        </div>
      ))}
    </div>
  );
}
