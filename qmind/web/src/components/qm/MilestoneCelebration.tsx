type Props = {
  phaseLabel: string;
  onDismiss?: () => void;
};

export function MilestoneCelebration({ phaseLabel, onDismiss }: Props) {
  return (
    <div className="qm-milestone" data-testid="milestone-celebration" role="status">
      <p>
        Marco alcançado: você está em <strong>{phaseLabel}</strong>. Continuamos
        valorizando conclusão, clareza e evidências — não “respostas certas”.
      </p>
      {onDismiss ? (
        <button type="button" className="qm-milestone__dismiss" onClick={onDismiss}>
          Ok
        </button>
      ) : null}
    </div>
  );
}
