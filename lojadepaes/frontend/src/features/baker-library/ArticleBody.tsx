import type { ReactNode } from "react";

const SAFE_HREF = /^(\/[a-zA-Z0-9\-._~/?#=&%]+|https:\/\/(www\.)?(alice\.cnptia\.embrapa\.br|embrapa\.br|gov\.br|www\.gov\.br)\/[a-zA-Z0-9\-._~/?#=&%]*)$/;

export function ArticleBody({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="library-article-body">
      {blocks.map((block, index) => {
        const heading = block.match(/^##\s+(.+)$/);
        if (heading) {
          return <h2 key={index}>{heading[1]}</h2>;
        }
        return <p key={index}>{renderInline(block)}</p>;
      })}
    </div>
  );
}

function renderInline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const pattern = /\[([^\]]+)\]\(([^)]+)\)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = pattern.exec(text))) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    const href = match[2];
    if (SAFE_HREF.test(href) && !href.startsWith("//")) {
      const external = href.startsWith("https://");
      parts.push(
        <a key={`l${key++}`} href={href} {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
          {match[1]}
        </a>,
      );
    } else {
      parts.push(match[1]);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return parts;
}
