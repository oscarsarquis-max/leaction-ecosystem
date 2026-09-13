import { useId, useState } from 'react';

export default function CopyOnceLink(props: {
  url: string;
  onDismiss: () => void;
}) {
  const headingId = useId();
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  return (
    <section className="copy-once" aria-labelledby={headingId} tabIndex={-1}>
      <h3 id={headingId}>Link emitido</h3>
      <p>Copie e guarde este endereço agora. Ele não poderá ser recuperado depois.</p>
      <div className="copy-once-row">
        <input
          className="copy-once-url"
          readOnly
          value={props.url}
          aria-label="Endereço público do convite"
        />
        <button
          type="button"
          className="button-primary"
          onClick={() => {
            try {
              void navigator.clipboard.writeText(props.url).then(
                () => {
                  setCopyState('copied');
                },
                () => {
                  setCopyState('failed');
                },
              );
            } catch {
              setCopyState('failed');
            }
          }}
        >
          Copiar endereço
        </button>
      </div>
      <p aria-live="polite">
        {copyState === 'copied'
          ? 'Endereço copiado'
          : copyState === 'failed'
            ? 'Não foi possível copiar automaticamente. Selecione o endereço e copie manualmente.'
            : ''}
      </p>
      <button type="button" className="button-secondary" onClick={props.onDismiss}>
        Concluir
      </button>
    </section>
  );
}
