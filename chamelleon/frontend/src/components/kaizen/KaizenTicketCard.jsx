import { getAndonBadges } from '../../utils/kaizenTicketMeta';

const SEVERITY_STYLES = {
  Critica: 'bg-red-100 text-red-800 ring-red-200',
  Alta: 'bg-orange-100 text-orange-800 ring-orange-200',
  Media: 'bg-amber-100 text-amber-900 ring-amber-200',
  Baixa: 'bg-slate-100 text-slate-600 ring-slate-200',
};

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
  const severityClass = SEVERITY_STYLES[ticket.severity] || SEVERITY_STYLES.Baixa;

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
      <div className="mb-2 flex flex-wrap gap-1">
        {ticket.severity && (
          <span
            className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${severityClass}`}
          >
            {ticket.severity}
          </span>
        )}
        {ticket.has_non_conformity && (
          <span className="inline-flex rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-900 ring-1 ring-inset ring-violet-200">
            NC
          </span>
        )}
        {ticket.operational_site_name && (
          <span className="inline-flex rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-800 ring-1 ring-inset ring-sky-200">
            {ticket.operational_site_name}
          </span>
        )}
        {badges.map((badge) => (
          <span
            key={badge.id}
            className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ring-1 ring-inset ${badge.className}`}
          >
            {badge.label}
          </span>
        ))}
      </div>

      {(ticket.is_escalated || ticket.escalated_to_sprint_id) && (
        <span className="mb-2 inline-flex rounded-full bg-emerald-900 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
          Escalado para Sprint
        </span>
      )}

      <h3 className="text-sm font-semibold leading-snug text-slate-800">{ticket.title}</h3>

      {preview && (
        <p className="mt-1.5 line-clamp-3 text-xs leading-relaxed text-slate-500">{preview}</p>
      )}

      {(ticket.owner_name || ticket.due_date) && (
        <p className="mt-2 text-[10px] text-slate-500">
          {ticket.owner_name ? `Resp.: ${ticket.owner_name}` : ''}
          {ticket.owner_name && ticket.due_date ? ' · ' : ''}
          {ticket.due_date ? `Prazo: ${ticket.due_date}` : ''}
        </p>
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
