/**
 * Campos de contexto empresarial para IA — chaves alinhadas ao PanelDX (somente leitura lá).
 * Chamelleon usa rótulos de negócio; persistência mantém nomes legados para Gênese futura.
 */

export const CONTEXT_FIELDS = [
  {
    id: 'dados_clientes',
    legacyKey: 'dados_etnograficos',
    label: 'Clientes',
    hint: 'Perfil dos clientes, segmentos atendidos, jornada, dores e expectativas.',
    placeholder:
      'Ex.: Base B2B em médias empresas de telecom; alta sensibilidade a SLA; decisores em TI e operações...',
    minChars: 40,
  },
  {
    id: 'dados_mercado',
    legacyKey: 'dados_mercado',
    label: 'Mercado e concorrência',
    hint: 'Concorrência, posicionamento, tendências setoriais e pressões externas.',
    placeholder:
      'Ex.: Mercado altamente regulado; concorrentes com ofertas digitais agressivas; demanda por fibra em expansão...',
    minChars: 40,
  },
  {
    id: 'clima_organizacional',
    legacyKey: 'clima_organizacional',
    label: 'Ambiente organizacional',
    hint: 'Cultura, liderança, prontidão para mudança e expectativas sobre transformação e IA.',
    placeholder:
      'Ex.: Cultura enxuta com resistência em áreas legadas; liderança aberta à inovação; equipes precisam de capacitação...',
    minChars: 40,
  },
];

export function readContextFromJourney(contextData = {}) {
  const values = {};
  CONTEXT_FIELDS.forEach((field) => {
    values[field.id] =
      contextData[field.id] ||
      contextData[field.legacyKey] ||
      '';
  });
  return values;
}

export function buildContextPayload(values) {
  const payload = {};
  CONTEXT_FIELDS.forEach((field) => {
    const trimmed = (values[field.id] || '').trim();
    payload[field.id] = trimmed;
    if (field.legacyKey !== field.id) {
      payload[field.legacyKey] = trimmed;
    }
  });
  return payload;
}

export function contextIsComplete(values) {
  return CONTEXT_FIELDS.every((field) => (values[field.id] || '').trim().length >= field.minChars);
}
