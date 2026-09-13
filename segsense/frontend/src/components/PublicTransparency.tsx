import { useId } from 'react';

export default function PublicTransparency(props: { open: boolean; headingId?: string }) {
  const generatedId = useId();
  const headingId = props.headingId ?? generatedId;
  if (!props.open) {
    return null;
  }
  return (
    <section className="public-transparency" aria-labelledby={headingId} tabIndex={-1}>
      <h2 id={headingId}>O que acontece agora?</h2>
      <ul>
        <li>O SegSense reconheceu apenas o contexto editorial associado a este convite.</li>
        <li>Nenhuma informação pessoal foi coletada nesta página.</li>
        <li>Nenhuma seguradora recebeu informações.</li>
        <li>Nenhuma cotação ou recomendação foi realizada.</li>
      </ul>
      <p>A continuidade desta jornada ainda não está disponível.</p>
    </section>
  );
}
