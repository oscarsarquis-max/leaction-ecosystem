import { getAndonBadges } from '../../utils/kaizenTicketMeta';

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

export default function KaizenTicketCard({
  ticket,
  stageId,
  isDragging,
  onDragStart,
  onDragEnd,
  onClick,
}) {
  const badges = stageId === 'Alerta' ? getAndonBadges(ticket) : [];
  const preview = (ticket.description || '').split('|')[0]?.trim();

  return (
    <article
      draggable
      onDragStart={(event) => onDragStart(event, ticket)}
      onDragEnd={onDragEnd}
      onClick={() => onClick?.(ticket)}
      className={[
        'cursor-grab rounded-xl border border-slate-200 bg-white p-3 shadow-sm transition active:cursor-grabbing',
        isDragging ? 'opacity-40 ring-2 ring-chameleon/30' : 'hover:border-slate-300 hover:shadow',
        stageId === 'Cinco_Porques' ? 'cursor-pointer hover:ring-2 hover:ring-sky-200' : '',
      ].join(' ')}
    >
      {badges.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {badges.map((badge) => (
            <span
              key={badge.id}
              className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${badge.className}`}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}

      <h3 className="text-sm font-semibold leading-snug text-slate-800">{ticket.title}</h3>

      {preview && (
        <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-slate-500">{preview}</p>
      )}

      <footer className="mt-3 flex items-center justify-between gap-2 text-[10px] text-slate-400">
        <span>{formatDate(ticket.updated_at || ticket.created_at)}</span>
        {stageId === 'Cinco_Porques' && (
          <span className="font-semibold text-sky-700">Investigar →</span>
        )}
      </footer>
    </article>
  );
}
