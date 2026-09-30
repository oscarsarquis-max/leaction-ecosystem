type OptionCardProps = {
  title: string;
  description?: string;
  tag?: string;
  selected: boolean;
  multiple?: boolean;
  onSelect: () => void;
};

export function splitPublicLabel(title: string): { primary: string; secondary?: string } {
  const match = title.match(/^(.+?) \(([^)]+)\)$/);
  if (!match) {
    return { primary: title };
  }
  return { primary: match[1], secondary: match[2] };
}

export function OptionCard({ title, description, tag, selected, multiple = false, onSelect }: OptionCardProps) {
  const { primary, secondary } = splitPublicLabel(title);
  return (
    <button
      className={`option ${selected ? "selected" : ""} ${multiple ? "multiple" : ""}`}
      aria-pressed={selected}
      type="button"
      onClick={onSelect}
    >
      <span className={multiple ? "check" : "radio"} aria-hidden="true">
        {multiple && selected ? "✓" : ""}
      </span>
      <span>
        <h3>
          {primary}
          {secondary ? <span className="option-title-en"> ({secondary})</span> : null}
        </h3>
        {description ? <p>{description}</p> : null}
        {tag ? <span className="tag">{tag}</span> : null}
      </span>
    </button>
  );
}
