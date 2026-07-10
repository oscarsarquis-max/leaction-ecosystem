const OCCURRENCE_LABELS = {
  acidente: 'Acidente',
  falta_material: 'Falta de material',
  queda_energia: 'Queda de energia',
  chuva_forte: 'Chuva forte',
  geral: 'Ocorrência geral',
  equipment_breakdown: 'Quebra de equipamento',
  delay_material: 'Espera de material',
  delay_rework: 'Retrabalho',
  delay_front: 'Falta de frente',
  ppe_non_compliance: 'EPI não conforme',
  excessive_absences: 'Faltas excessivas',
  meta_nao_atingida: 'Meta não atingida',
};

function extractRdo(report) {
  const raw = report?.raw_payload;
  if (raw && typeof raw === 'object') return raw;
  return {};
}

export function getReportDate(report) {
  return report?.report_date || report?.date || '—';
}

export function getImpedimentTags(report) {
  const tags = [];
  const rdo = extractRdo(report);

  if (report?.goal_achieved === false || rdo.goal_achieved === false) {
    tags.push({ id: 'meta', label: 'Meta não atingida', tone: 'danger' });
  }
  if (rdo.delay_waiting_material) {
    tags.push({ id: 'delay_material', label: 'Espera de material', tone: 'warning' });
  }
  if (rdo.delay_rework) {
    tags.push({ id: 'delay_rework', label: 'Retrabalho', tone: 'warning' });
  }
  if (rdo.delay_lack_of_front) {
    tags.push({ id: 'delay_front', label: 'Falta de frente', tone: 'warning' });
  }
  if (rdo.ppe_compliant === false) {
    tags.push({ id: 'ppe', label: 'EPI não conforme', tone: 'danger' });
  }

  for (const item of rdo.occurrences || []) {
    if (!item || typeof item !== 'object') continue;
    const type = String(item.type || 'geral').toLowerCase();
    const label = OCCURRENCE_LABELS[type] || type.replace(/_/g, ' ');
    tags.push({ id: `occ-${type}-${tags.length}`, label, tone: 'danger' });
  }

  for (const item of rdo.equipment_statuses || []) {
    if (!item || typeof item !== 'object') continue;
    const status = String(item.status || '').toLowerCase();
    if (status === 'parado por quebra') {
      const name = item.equipment_name || 'Equipamento';
      tags.push({
        id: `eq-${tags.length}`,
        label: `Quebra: ${name}`,
        tone: 'danger',
      });
    }
  }

  if (report?.impediment_details && !tags.some((t) => t.id === 'meta')) {
    tags.push({ id: 'impediment', label: 'Impeditivo registrado', tone: 'warning' });
  }

  return tags;
}

export function formatOccurrenceType(type) {
  const key = String(type || 'geral').toLowerCase();
  return OCCURRENCE_LABELS[key] || key.replace(/_/g, ' ');
}

export function buildRdoDetailSections(report) {
  const rdo = extractRdo(report);
  const occurrences = (rdo.occurrences || []).map((item, index) => ({
    id: `occ-${index}`,
    type: formatOccurrenceType(item?.type),
    location: item?.exact_location || '—',
    whatHappened: item?.what_happened || item?.description || '—',
    immediateAction: item?.immediate_action_taken || '',
    safetyNotes: item?.safety_ppe_notes || '',
  }));

  const equipment = (rdo.equipment_statuses || []).map((item, index) => ({
    id: `eq-${index}`,
    name: item?.equipment_name || 'Equipamento',
    status: item?.status || '—',
    quantity: item?.quantity,
    remarks: item?.remarks || '',
  }));

  const delays = [];
  if (rdo.delay_waiting_material) delays.push('Equipe parada esperando material');
  if (rdo.delay_rework) delays.push('Retrabalho no turno');
  if (rdo.delay_lack_of_front) delays.push('Falta de frente de trabalho');

  return {
    meta: {
      sprintDailyGoal: report?.sprint_daily_goal || rdo.sprint_daily_goal || '—',
      goalAchieved:
        report?.goal_achieved ?? rdo.goal_achieved ?? null,
      impedimentDetails: report?.impediment_details || rdo.impediment_details || '—',
      mitigationAction: report?.mitigation_action || rdo.mitigation_action || '—',
      preventiveAction: report?.preventive_action || rdo.preventive_action || '—',
    },
    occurrences,
    equipment,
    delays,
    ppe: {
      compliant: rdo.ppe_compliant,
      details: rdo.ppe_compliant_details || '',
    },
    workforce: rdo.workforce || [],
    notes: rdo.general_notes || rdo.notes || '',
  };
}
