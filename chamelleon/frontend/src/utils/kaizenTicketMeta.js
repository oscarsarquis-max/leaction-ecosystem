import { ANDON_BADGES } from '../constants/kaizen';

/** Extrai local e sintoma a partir da descrição gerada pelo Andon. */
export function parseOccurrenceFromTicket(ticket) {
  const description = (ticket?.description || '').trim();
  const title = (ticket?.title || '').trim();

  let location = '';
  let whatHappened = description || title;
  let immediateAction = '';

  if (description.includes('Local:')) {
    const parts = description.split('|').map((part) => part.trim());
    for (const part of parts) {
      if (part.startsWith('Local:')) {
        location = part.replace(/^Local:\s*/i, '').trim();
      } else if (part.startsWith('Ação na hora:')) {
        immediateAction = part.replace(/^Ação na hora:\s*/i, '').trim();
      } else if (!part.startsWith('EPI/Segurança:')) {
        whatHappened = part;
      }
    }
  }

  if (!location && /local:/i.test(description)) {
    const match = description.match(/Local:\s*([^|]+)/i);
    location = match?.[1]?.trim() || '';
  }

  return {
    title,
    location: location || 'Local não informado no RDO',
    whatHappened: whatHappened || 'Ocorrência registrada no Diário de Obra',
    immediateAction,
  };
}

export function getAndonBadges(ticket) {
  return ANDON_BADGES.filter((badge) => badge.match(ticket));
}

export function emptyKanbanBoard() {
  return {
    Alerta: [],
    Contencao: [],
    Cinco_Porques: [],
    Padronizacao: [],
    Concluido: [],
  };
}
