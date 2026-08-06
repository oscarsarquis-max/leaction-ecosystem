import { Link } from "react-router-dom";

type Props = {
  title: string;
  description: string;
  reason: string;
  actionText: string;
  href: string;
};

export function JourneyNextAction({
  title,
  description,
  reason,
  actionText,
  href,
}: Props) {
  return (
    <section
      className="org-journey__nba"
      data-testid="org-journey-next-action"
      aria-labelledby="org-journey-nba-title"
    >
      <p className="org-journey__nba-kicker">Próxima ação prioritária</p>
      <h2 id="org-journey-nba-title" className="org-journey__nba-title">
        {title}
      </h2>
      <p className="org-journey__nba-desc">{description}</p>
      <p className="org-journey__nba-reason">
        <span className="font-semibold text-[var(--qm-ink)]">Por quê: </span>
        {reason}
      </p>
      <Link to={href} className="qm-btn-primary mt-4 inline-flex" data-testid="org-journey-continue">
        {actionText}
      </Link>
    </section>
  );
}
