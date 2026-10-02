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
          <strong>
            {item.value}
            {item.hint ? <span className="count-aux"> {item.hint}</span> : null}
          </strong>
        </div>
      ))}
    </div>
  );
}
