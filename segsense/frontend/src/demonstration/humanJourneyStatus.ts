export function humanJourneyStatus(status: string): string {
  switch (status) {
    case 'PRE_PROPOSAL_AVAILABLE':
      return 'Pré-proposta demonstrativa disponível';
    case 'SIMULATED_QUOTE_AVAILABLE':
      return 'Cotação simulada disponível';
    case 'REJECTED':
      return 'Pedido recusado nesta demonstração';
    case 'MOCK_UNAVAILABLE':
      return 'Provedor ilustrativo indisponível';
    case 'SPIDER_UNAVAILABLE':
      return 'Spider indisponível';
    case 'MISSING_CONTEXT':
      return 'Contexto insuficiente';
    case 'AMBIGUOUS':
      return 'Contexto ou intenção ambíguos';
    case 'NO_COMPATIBLE_CAPABILITY':
      return 'Nenhuma possibilidade disponível neste ambiente demonstrativo';
    case 'INCOMPLETE_CANONICAL':
      return 'A resposta da Spider não confirmou decisão e retorno de provedor';
    default:
      return status;
  }
}
