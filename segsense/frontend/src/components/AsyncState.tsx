import { type ReactNode } from 'react';

type AsyncStateProps = {
  loading: boolean;
  loadingLabel: string;
  error?: string | null;
  empty?: boolean;
  emptyLabel?: string;
  children: ReactNode;
};

export default function AsyncState(props: AsyncStateProps) {
  return (
    <div aria-busy={props.loading} aria-live="polite">
      {props.loading ? <p role="status">{props.loadingLabel}</p> : null}
      {props.error ? <p role="alert">{props.error}</p> : null}
      {!props.loading && !props.error && props.empty ? <p>{props.emptyLabel}</p> : null}
      {!props.loading && !props.error && !props.empty ? props.children : null}
    </div>
  );
}
