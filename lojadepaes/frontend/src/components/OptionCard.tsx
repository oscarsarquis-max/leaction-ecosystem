type OptionCardProps = {
  title: string;
  description?: string;
  tag?: string;
  selected: boolean;
  onSelect: () => void;
};

export function OptionCard({ title, description, tag, selected, onSelect }: OptionCardProps) {
  return (
    <button className={`option ${selected ? "selected" : ""}`} aria-pressed={selected} type="button" onClick={onSelect}>
      <span className="radio" aria-hidden="true" />
      <span>
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
        {tag ? <span className="tag">{tag}</span> : null}
      </span>
    </button>
  );
}
