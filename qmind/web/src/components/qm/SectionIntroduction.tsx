type Props = {
  title: string;
  body: string;
  expectedResult?: string;
};

export function SectionIntroduction({ title, body, expectedResult }: Props) {
  return (
    <div className="qm-section-intro" data-testid="section-introduction">
      <h2 className="qm-section-intro__title">{title}</h2>
      <p className="qm-section-intro__body">{body}</p>
      {expectedResult ? (
        <p className="qm-section-intro__result">
          <span className="qm-meta-label">Resultado desta etapa</span>
          {expectedResult}
        </p>
      ) : null}
    </div>
  );
}
