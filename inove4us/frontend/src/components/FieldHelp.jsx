/**
 * Micro-copy de ajuda sob campos (muted) + tooltip nativo opcional no [?].
 */
export default function FieldHelp({ children, tip }) {
  if (!children && !tip) return null
  return (
    <p className="mt-1.5 flex items-start gap-1.5 text-xs leading-relaxed text-bordo-soft">
      {tip ? (
        <span
          className="mt-0.5 inline-flex h-4 w-4 shrink-0 cursor-help items-center justify-center rounded-full border border-brand-200 bg-brand-50 text-[10px] font-bold text-bordo-soft"
          title={tip}
          aria-label={tip}
        >
          ?
        </span>
      ) : null}
      {children ? <span>{children}</span> : null}
    </p>
  )
}
