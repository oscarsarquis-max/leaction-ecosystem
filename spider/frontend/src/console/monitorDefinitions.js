export const DEFINITIONS = {
  origin: ['Origem e entrada', 'Identifica quem iniciou a interação e por qual entrada. Satélite de origem, componente que processa e executor são identidades diferentes.'],
  identity: ['Identidade, contrato e segurança', 'Autentica o satélite, valida o Satellite Contract, a empresa autorizada e as proteções de replay/idempotência.'],
  context: ['Contexto e intenção', 'Reúne as informações permitidas e sua proveniência para compreender a necessidade. O Monitor não reconstitui dados que não foram registrados.'],
  objective: ['Objetivo / intenção', 'Declara o que se pretende alcançar. A intenção de negócio não escolhe diretamente um sistema ou provider.'],
  interpretation: ['Interpretação', 'Normaliza a entrada semântica. IA é opcional; sua utilização precisa de evidência explícita.'],
  intent: ['Intent Contract', 'Representação estruturada da intenção, do contexto e das restrições que serão avaliadas pelo Spider.'],
  policy: ['Policy / contrato', 'Avalia condições e restrições de autorização e execução. Validação do Satellite Contract não comprova, isoladamente, uma Policy versionada.'],
  plan: ['Plano de execução', 'Organiza as operações necessárias. O plano persistido descreve etapas; a existência do plano não significa que todas tenham executado.'],
  capabilities: ['Business Capabilities', 'Expressam o que precisa ser feito no negócio, independentemente do sistema que realizará a operação.'],
  resolution: ['Resolução', 'Associa a capacidade a uma rota e a um executor disponível segundo a governança aplicada.'],
  execution: ['Execução', 'Realiza as operações e registra tentativas, resultados, falhas e esperas. Cada etapa pode ter um estado diferente.'],
  result: ['Resultado', 'Registra a resposta obtida. Sucesso técnico não significa necessariamente que o objetivo de negócio foi integralmente atendido.'],
  async: ['Espera/callback', 'Wait, inbox, outbox e reconciliação. Só são atravessados quando a transação realmente espera um sinal ou callback.'],
  observe: ['Persistência e evidências', 'Ports de persistência, Operational Event Store e o read model do Monitor. A jornada persistida sobrevive ao restart.'],
  discovery: ['Descoberta', 'Pagamento observado no ActionHub Pay e correlacionado pelo sincronismo. Não afirma que o pagamento percorreu a Spider antes da descoberta.'],
  financial: ['Estado financeiro', 'Estado financeiro registrado a partir da operação observada no provedor, separado do processamento interno da Spider.'],
};

export const FIELD_LABELS = {
  order: 'Ordem', attemptNumber: 'Número da tentativa', disposition: 'Certeza do resultado', intent: 'Intenção', policyRef: 'Referência da policy', planId: 'Identificador do plano',
  planStatus: 'Estado do plano', capabilityRef: 'Capacidade', routeCode: 'Rota', routeRef: 'Rota',
  provenance: 'Proveniência', provider: 'Provider', model: 'Modelo de IA', executor: 'Executor',
  stepRef: 'Etapa', state: 'Estado', attemptCount: 'Tentativas', durationMs: 'Duração (ms)',
  startedAt: 'Início', completedAt: 'Conclusão', occurredAt: 'Ocorrência', decision: 'Decisão',
  component: 'Componente', eventType: 'Evento', safeErrorCode: 'Código de erro',
  retryPolicyRef: 'Policy de retry', waitPolicyRef: 'Policy de espera', adapterBindingRef: 'Vínculo do adapter',
};
