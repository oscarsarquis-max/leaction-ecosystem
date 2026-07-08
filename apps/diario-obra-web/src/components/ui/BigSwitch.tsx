interface Props {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

/** Switch grande para perguntas sim/não de atraso (padrão: desligado = não). */
export default function BigSwitch({ label, checked, onChange, disabled = false }: Props) {
  return (
    <div className="flex min-h-16 items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <p className="flex-1 text-base font-semibold leading-snug text-slate-800">{label}</p>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={[
          'relative h-10 w-[4.5rem] shrink-0 rounded-full transition-colors',
          checked ? 'bg-amber-500' : 'bg-slate-200',
          disabled ? 'opacity-50' : '',
        ].join(' ')}
      >
        <span
          className={[
            'absolute top-1 h-8 w-8 rounded-full bg-white shadow-md transition-transform',
            checked ? 'translate-x-9' : 'translate-x-1',
          ].join(' ')}
        />
      </button>
    </div>
  );
}
