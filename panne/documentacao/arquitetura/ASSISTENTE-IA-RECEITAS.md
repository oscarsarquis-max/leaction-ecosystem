# Assistente de IA de receitas

Reutiliza `ModelGateway`, `BedrockClaudeGateway`, `FakeModelGateway`, Bedrock Converse, schemas estritos, orquestração existente, grounding determinístico e revisão humana. Não há segundo gateway, orquestrador ou grounding.

## Fluxos

- **Criar:** objetivo → evidências → proposta → validação → revisão → rascunho atômico (produto, formulação, versão 1).
- **Adaptar:** versão-base congelada → evidências → diff → aceite/rejeição por item → nova versão em rascunho. A base não é editada nem publicada.

A IA gera proposta estruturada. Motores determinísticos recalculam bruto, percentual do padeiro, escala e nutrição. Materialização cria somente rascunho. Não publica, não aprova, não cria ingrediente, não declara conformidade e não comanda produção.

## Estados

`requested`, `retrieving_evidence`, `grounding_insufficient`, `generating`, `validation_failed`, `awaiting_review`/`draft`, `accepted`, `rejected`, `materialized`, `cancelled` (mais `expired`/`invalid` herdados).

Proposta e evidências são imutáveis. Nova geração cria nova proposta.

## Permissões

`recipe.ai.propose`, `recipe.ai.review` e `recipe.ai.materialize` são distintas. Owner, admin e responsável técnico as recebem. Revisor regulatório só revisa. Padeiro e viewer não geram nem materializam.

## Guardrails

Validação de entrada, filtros de recuperação, isolamento, prompt versionado (`panne_recipe_assistant` v2), Guardrail da AWS quando configurado (obrigatório em produção), schema estrito, IDs permitidos, validação determinística, verificação de citações e revisão humana.

Fake explícito permanece permitido em desenvolvimento e testes. Bedrock vivo é opt-in.
