import { Link } from "react-router-dom";

type Props = {
  label: string;
  href: string;
  hint?: string;
  primary?: boolean;
};

export function NextBestAction({ label, href, hint, primary = true }: Props) {
  return (
    <div className="qm-nba" data-testid="next-best-action">
      {hint ? <p className="qm-nba__hint">{hint}</p> : null}
      <Link
        to={href}
        className={primary ? "qm-btn-primary" : "qm-btn-secondary"}
        data-testid="continue-audit"
      >
        {label}
      </Link>
    </div>
  );
}
