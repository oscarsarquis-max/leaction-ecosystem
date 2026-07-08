interface Props {
  label: string;
  value: boolean | null;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}

export default function YesNoToggle({ label, value, onChange, disabled = false }: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-sm font-semibold text-slate-800">{label}</p>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(true)}
          className={[
            'min-h-14 rounded-2xl text-lg font-bold',
            value === true
              ? 'bg-emerald-600 text-white shadow-md'
              : 'bg-slate-100 text-slate-700',
          ].join(' ')}
        >
          Sim
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(false)}
          className={[
            'min-h-14 rounded-2xl text-lg font-bold',
            value === false
              ? 'bg-red-600 text-white shadow-md'
              : 'bg-slate-100 text-slate-700',
          ].join(' ')}
        >
          Não
        </button>
      </div>
    </div>
  );
}
