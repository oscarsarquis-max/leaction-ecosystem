import { getIndustryLabels } from '../../utils/industryLabels';
import { buildRdoDetailSections, getReportDate } from '../../utils/rdoReportUtils';

function GoalBadge({ achieved }) {
  if (achieved === true) {
    return (
      <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
        Meta atingida
      </span>
    );
  }
  if (achieved === false) {
    return (
      <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800">
        Meta não atingida
      </span>
    );
  }
  return (
    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
      Sem resposta de meta
    </span>
  );
}

export default function RdoDetailsModal({ report, onClose }) {
  if (!report) return null;

  const labels = getIndustryLabels(report.industry_type);
  const sections = buildRdoDetailSections(report);
  const hasRawPayload = Boolean(report.raw_payload && typeof report.raw_payload === 'object');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="rdo-details-title"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Relatório completo · {getReportDate(report)}
            </p>
            <h2 id="rdo-details-title" className="mt-1 text-lg font-semibold text-slate-900">
              {labels.unit} {report.site_name}
            </h2>
            {report.site_location && (
              <p className="mt-1 text-sm text-slate-600">{report.site_location}</p>
            )}
          </div>
          <button
            type="button"
            className="rounded-lg border border-slate-200 px-2 py-1 text-sm text-slate-600 hover:bg-slate-50"
            onClick={onClose}
          >
            Fechar
          </button>
        </div>

        {!hasRawPayload && report.pending && (
          <p className="mt-5 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Nenhum RDO assinado neste dia para esta unidade.
          </p>
        )}

        {!hasRawPayload && !report.pending && (
          <p className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Dados detalhados indisponíveis. Exibindo campos consolidados do farol.
          </p>
        )}

        <section className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-900">Metas do dia</h3>
            <GoalBadge achieved={sections.meta.goalAchieved} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Meta da sprint</p>
            <p className="mt-1 text-sm text-slate-800">{sections.meta.sprintDailyGoal}</p>
          </div>
        </section>

        <section className="mt-4 space-y-3 rounded-xl border border-red-100 bg-red-50/40 p-4">
          <h3 className="text-sm font-semibold text-red-900">Impeditivos e ações</h3>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Impeditivo</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
              {sections.meta.impedimentDetails}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Mitigação</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
              {sections.meta.mitigationAction}
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-red-800">Prevenção</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-slate-800">
              {sections.meta.preventiveAction}
            </p>
          </div>
        </section>

        {sections.delays.length > 0 && (
          <section className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-4">
            <h3 className="text-sm font-semibold text-amber-900">Atrasos / paradas</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-800">
              {sections.delays.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        )}

        {sections.occurrences.length > 0 && (
          <section className="mt-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Ocorrências</h3>
            {sections.occurrences.map((occ) => (
              <article
                key={occ.id}
                className="rounded-xl border border-orange-200 bg-orange-50/40 p-4 text-sm"
              >
                <p className="font-semibold text-orange-900">{occ.type}</p>
                <p className="mt-2 text-slate-700">
                  <span className="font-medium">Onde:</span> {occ.location}
                </p>
                <p className="mt-1 text-slate-700">
                  <span className="font-medium">O que aconteceu:</span> {occ.whatHappened}
                </p>
                {occ.immediateAction && (
                  <p className="mt-1 text-slate-700">
                    <span className="font-medium">Ação na hora:</span> {occ.immediateAction}
                  </p>
                )}
                {occ.safetyNotes && (
                  <p className="mt-1 text-slate-700">
                    <span className="font-medium">EPI/Segurança:</span> {occ.safetyNotes}
                  </p>
                )}
              </article>
            ))}
          </section>
        )}

        {sections.equipment.length > 0 && (
          <section className="mt-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Equipamentos</h3>
            {sections.equipment.map((eq) => (
              <article key={eq.id} className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
                <p className="font-semibold text-slate-900">{eq.name}</p>
                <p className="mt-1 text-slate-700">Status: {eq.status}</p>
                {eq.quantity != null && (
                  <p className="mt-1 text-slate-700">Quantidade: {eq.quantity}</p>
                )}
                {eq.remarks && <p className="mt-1 text-slate-600">{eq.remarks}</p>}
              </article>
            ))}
          </section>
        )}

        {sections.ppe.compliant === false && (
          <section className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm">
            <h3 className="font-semibold text-red-900">EPI / Segurança</h3>
            <p className="mt-1 text-slate-800">
              {sections.ppe.details || 'Não conformidade de EPI registrada no RDO.'}
            </p>
          </section>
        )}

        {sections.notes && (
          <section className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm">
            <h3 className="font-semibold text-slate-900">Observações gerais</h3>
            <p className="mt-1 whitespace-pre-wrap text-slate-800">{sections.notes}</p>
          </section>
        )}
      </div>
    </div>
  );
}
