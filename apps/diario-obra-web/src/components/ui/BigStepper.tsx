interface Props {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
}

export default function BigStepper({
  label,
  value,
  onChange,
  min = 0,
  max = 999,
  disabled = false,
}: Props) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3">
      <p className="text-sm font-semibold text-slate-800">{label}</p>
      <div className="mt-2 flex items-center justify-between gap-3">
        <button
          type="button"
          disabled={disabled || value <= min}
          onClick={() => onChange(Math.max(min, value - 1))}
          className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-2xl font-bold text-slate-800 disabled:opacity-40"
        >
          −
        </button>
        <span className="min-w-[3rem] text-center text-3xl font-bold text-emerald-700">{value}</span>
        <button
          type="button"
          disabled={disabled || value >= max}
          onClick={() => onChange(Math.min(max, value + 1))}
          className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-600 text-2xl font-bold text-white disabled:opacity-40"
        >
          +
        </button>
      </div>
    </div>
  );
}
