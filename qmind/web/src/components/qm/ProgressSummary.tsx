type Item = { label: string; value: string };

type Props = {
  title?: string;
  caption?: string;
  items: Item[];
};

export function ProgressSummary({
  title = "Resumo do trabalho",
  caption,
  items,
}: Props) {
  return (
    <section className="qm-progress-summary" data-testid="progress-summary">
      <h2 className="qm-progress-summary__title">{title}</h2>
      {caption ? <p className="qm-progress-summary__caption">{caption}</p> : null}
      <div className="qm-progress-summary__grid">
        {items.map((item) => (
          <div key={item.label} className="qm-stat">
            <p className="qm-stat__label">{item.label}</p>
            <p className="qm-stat__value">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
