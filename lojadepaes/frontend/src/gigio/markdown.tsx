import { Fragment, type ReactNode } from "react";

const SAFE_HREF = /^\/[a-zA-Z0-9\-._~/?#=&%]+$/;

export function SafeMarkdown({ text }: { text: string }): ReactNode {
  const cleaned = text
    .replace(/\r\n/g, "\n")
    .replace(/<\/?(invoke|parameter)\b[^>]*>/gi, "")
    .replace(/<[^>\n]+>/g, "")
    .replace(/ +-\s+\*\*/g, "\n- **");
  const blocks = cleaned
    .replace(/^\s*---+\s*$/gm, "\n\n")
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);
  return (
    <>
      {blocks.map((block, index) => renderBlock(block, index))}
    </>
  );
}

function renderBlock(block: string, index: number): ReactNode {
  const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
  const groups: { kind: "list" | "text"; lines: string[] }[] = [];
  for (const line of lines) {
    const kind = /^([-*]|\d+\.)\s+\S/.test(line) ? "list" : "text";
    const current = groups[groups.length - 1];
    if (!current || current.kind !== kind) {
      groups.push({ kind, lines: [line] });
    } else {
      current.lines.push(line);
    }
  }
  return (
    <Fragment key={index}>
      {groups.map((group, groupIndex) =>
        group.kind === "list" ? (
          <ul key={groupIndex}>
            {group.lines.map((line, lineIndex) => (
              <li key={lineIndex}>{renderInline(line.replace(/^([-*]|\d+\.)\s+/, ""))}</li>
            ))}
          </ul>
        ) : (
          <p key={groupIndex}>
            {group.lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {lineIndex > 0 ? <br /> : null}
                {renderInline(line)}
              </span>
            ))}
          </p>
        ),
      )}
    </Fragment>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = pattern.exec(text))) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    if (match[1]) {
      parts.push(<strong key={`b${key++}`}>{match[1]}</strong>);
    } else {
      const href = match[3];
      if (SAFE_HREF.test(href) && !href.startsWith("//")) {
        parts.push(
          <a key={`l${key++}`} href={href}>
            {match[2]}
          </a>,
        );
      } else {
        parts.push(match[2]);
      }
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts;
}
