import { useEffect, useId, useRef, type ReactNode } from 'react';

type DestructiveConfirmationProps = {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  confirmDisabled?: boolean;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  returnFocusTo: HTMLElement | null;
};

function focusable(root: HTMLElement): HTMLElement[] {
  return [
    ...root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ].filter((element) => !element.hasAttribute('disabled'));
}

export default function DestructiveConfirmation({
  open,
  title,
  children,
  confirmLabel,
  cancelLabel,
  confirmDisabled,
  busy,
  onConfirm,
  onCancel,
  returnFocusTo,
}: DestructiveConfirmationProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const previous = returnFocusTo;
    const node = dialogRef.current;
    cancelRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== 'Tab' || node == null) {
        return;
      }
      const items = focusable(node);
      if (items.length === 0) {
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      if (first == null || last == null) {
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      previous?.focus();
    };
  }, [open, onCancel, returnFocusTo]);

  if (!open) {
    return null;
  }

  return (
    <div className="dialog-backdrop">
      <div
        ref={dialogRef}
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <h2 id={titleId}>{title}</h2>
        {children}
        <div className="dialog-actions">
          <button ref={cancelRef} type="button" className="button-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className="button-danger"
            disabled={confirmDisabled === true || busy === true}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
