# SPIDERBANK-CONTRACT-001 — Execução de simulação de capital de giro

**Status:** DRAFT v0.1 — definição proposta para discussão  
**Data:** 17 de setembro de 2026  
**Escopo:** primeiro item da integração: contrato entre Spider e sistema executor de crédito.  
**Autorização vigente:** análise e definição documental. **Não autoriza alterações no Core ou no mock.**

## 1. Objetivo

Definir a execução da capability existente `SIMULATE_WORKING_CAPITAL` por um sistema no papel de provider. Na primeira fatia, esse sistema é representado pelo projeto `C:\Projetos\mock-sistemas-credito`.

Spider mantém a autoridade sobre interpretação, Intent Contract, políticas, plano e resolução. O sistema executor recebe somente os parâmetros necessários à simulação e devolve seu resultado. A resposta do executor não constitui aprovação de crédito.

## 2. Evidências e alcance da inspeção

Foram lidos nesta etapa o handler atual do mock, o schema de resposta de provider em satellite/1.0, a interface `ProviderCapabilityPort` e o relatório em `spider-bank/documents/SPIDERBANK-PRM-001.md`.

Constatações:

- O mock usa contrato local `credit-mock/0.1`, finalidade local `WORKING_CAPITAL_SIMULATION`, providerId `credit-provider-mock` e header `X-Credit-Mock-Credential`.
- O schema de resposta existente já admite ACCEPTED, COMPLETED, REJECTED, FAILED e PENDING. O colapso de estados em indisponibilidade está no tratamento da integração atual (`HttpProviderCapabilityAdapter` / `ExecutionResult.unavailable()`), não no enum do schema.
- A interface de resultado atual contém projeção de seguros (`ResultItem`, `quote`) e não preserva explicitamente motivos, `missingFields`, parcelas nem `offerable` do perfil de crédito.
- O plano `SEEK_WORKING_CAPITAL` contém outras capabilities `NOT_AVAILABLE`. Integrar só este executor não habilita o plano inteiro.

Não foram executados novos testes nem alterados arquivos do Spider ou do mock nesta etapa.

## 3. Proposta arquitetural

Recomenda-se um **perfil de execução de crédito versionado**, com schema de pedido e resposta próprios, mantendo a separação entre envelope de execução e resultado específico da capability.

Endpoint do executor:

`POST /v1/provider/capabilities/SIMULATE_WORKING_CAPITAL/executions`

O satélite continua no Satellite Contract; não escolhe endpoint ou provider.

`credit-mock/0.1` permanece exclusivamente local. Não é contrato oficial do Spider.

**Identificadores existentes:** capability `SIMULATE_WORKING_CAPITAL`; identidade técnica `credit-provider-mock`. O nome de produto “Mock de Sistemas de Crédito” não exige mudar essa identidade nesta etapa.

A numeração oficial do perfil e a pasta no repositório ficam para depois da aprovação desta definição — e só entram no Core com autorização específica (item 2).

## 4. Pedido — definição proposta

| Campo | Semântica e regra proposta |
|---|---|
| contractVersion | Versão explícita do perfil aceito por ambos os lados; ainda sem numeração oficial. |
| requestId | Identificador da execução solicitado pelo Spider. |
| correlationId | Correlação mantida pelo Spider entre interação e execução. |
| decisionId | Referência à decisão governada que autorizou a chamada. |
| capabilityId | Constante `SIMULATE_WORKING_CAPITAL`; deve coincidir com o path. |
| capabilityVersion | Versão da capability acordada; não confundir com versão do envelope. |
| purpose | Proposta `WORKING_CAPITAL_SIMULATION`, sujeita a alinhamento com a política de finalidade do Spider. |
| dataClassification | Classificação efetiva dos inputs. Nesta fatia, somente sintéticos PUBLIC/INTERNAL. |
| requestedAt | Instante UTC válido gerado pelo Spider. |
| inputs.principalCents | Valor solicitado, inteiro em centavos; não é limite aprovado. |
| inputs.termMonths | Prazo solicitado em meses inteiros. |

Identificadores: 8 a 80 caracteres ASCII `[A-Za-z0-9_-]`, condicionado à compatibilidade com os geradores do Spider.

Limites de **fixture** (não política de crédito): principal 10.000–100.000.000 centavos; prazo 1–36 meses.

Perfil inicial somente BRL, explícito. Sem conversão cambial. Sem callback. Sem execução assíncrona real.

Campos extras rejeitados. Fora do payload: contexto integral, texto do cliente, nome, documento, Intent, plano, credenciais de outros sistemas, taxa imposta pelo chamador.

## 5. Dados faltantes e cenários de teste

Principal e prazo são necessários para concluir. Ausência → PENDING/`MISSING_CONTEXT` com os nomes exatos dos campos. Inválido → erro de validação. Nunca default de montante ou prazo.

`scenarioKey` permanece no contrato **local** do test double. Não é parâmetro bancário nem escolha do cliente. A seleção de cenário na integração futura é item do adapter/configuração de testes.

`syntheticSupportingContext` da fixture, quando MISSING_CONTEXT é forçado com valores presentes, **não** vira pedido genérico de documentos ao cliente.

## 6. Resposta — definição proposta

Envelope: contractVersion, requestId, correlationId, capabilityId, providerId, status, reasonCodes, executedAt, providerReference, resultado específico.

O Spider valida perfil, identidade do executor resolvido e correlação. HTTP 200 isolado não comprova sucesso. Resposta incompatível ou correlação divergente = falha de integração, sem números na experiência.

Marcadores obrigatórios nesta fatia:

- `kind = SYNTHETIC_WORKING_CAPITAL_SIMULATION`
- `origin = NON_BINDING_DEMO`
- `testDouble = true`, `boundary = MOCK_ONLY`, `offerable = false`
- Aviso: simulação ilustrativa, sem valor comercial, sem oferta, aprovação ou contratação

COMPLETED: BRL, principal, prazo, taxa fictícia identificada, regra de cálculo, juros, total, parcelas, premissas. Soma das parcelas = total em centavos.

Cálculo atual (100 bps/mês, juros simples) é fixture. Não é Price, SAC, CET, mercado, tributo, garantia ou risco.

PENDING/REJECTED: não apresentar condições calculadas. Pendência humana sintética: `reviewQueued = false`.

## 7. Estados e falhas

| Evento do executor | Semântica a preservar no Spider | Efeito permitido na experiência |
|---|---|---|
| COMPLETED válido | Resultado sintético concluído | Simulação com premissas e marcação ilustrativa |
| PENDING + MISSING_CONTEXT | Faltam parâmetros identificados | Pedir só os campos necessários |
| PENDING + SYNTHETIC_HUMAN_REVIEW | Fixture, sem fila real | Não dizer que um analista recebeu o caso |
| REJECTED + SYNTHETIC_SCENARIO_REJECTED | Recusa sintética do executor | Não confundir com POLICY_REJECTED nem recusa real |
| 503, timeout, conexão | Executor indisponível | Sem números substitutos |
| Payload/auth/correlação inválidos | Falha técnica | Não apresentar como inelegibilidade ou aprovação |

Mapeamento para status externos do Satellite Contract (`READY`, `MISSING_CONTEXT`, `PROVIDER_UNAVAILABLE`, `REJECTED`, `AMBIGUOUS`) fica no item da jornada. Este DRAFT não inventa códigos de satélite.

ACCEPTED não será emitido nesta fatia (sem assíncrono).

## 8. Transporte, segurança e repetição

Loopback, 8.192 bytes, segredo fora do frontend e do código. Header/credencial do executor de crédito, sem reutilizar a identidade de seguros.

Primeira integração proposta: prazo finito, **sem retry automático** até haver política. `retryable` não autoriza repetição ilimitada.

`providerReference` atual não é idempotência persistente. Não prometer exatamente-uma-vez.

## 9. Critérios para uma futura implementação contratual

1. Pedido mínimo válido aceito; finalidade, versão e capability incompatíveis rejeitadas.
2. Campos extras, dados pessoais e contexto completo rejeitados.
3. Montante ou prazo ausentes → pendência específica; inválidos → erro.
4. COMPLETED, PENDING e REJECTED distintos de indisponibilidade.
5. Resposta inválida, identidade ou correlação erradas não projetadas ao cliente.
6. Marcadores de simulação preservados; parcelas somam o total.
7. Contratos e comportamento de seguros preservados.
8. Teste de contrato isolado ≠ prova da jornada completa.

## 10. Sequência de decisões

**Item 1, agora:** aprovar ou ajustar esta definição. Aprovação documental **não** autoriza editar o Core.

**Item 2, posterior:** proposta concreta de schemas, adapter, projeções e testes — autorização específica.

**Seguintes:** registro/resolução do executor; depois jornada do satélite, contexto governado e demais capabilities do plano.

Integração do provider e jornada SAT-003 de crédito são complementares, não alternativas. O escopo da relação Spider × SpiderBank passou a ser **SPIDERBANK-ARQ-002** (Experience Satellite); este contrato permanece o perfil Spider ↔ executor.

**Nada neste documento muda a disponibilidade da capability, aprova o ADR principal ou autoriza scaffold do SpiderBank.**

---

## Análise desta conversa (17 set 2026) — sem alterar Core/mock

Confirmações:

1. Enum de status do schema satellite/1.0 de resultado de provider já inclui ACCEPTED, COMPLETED, REJECTED, FAILED, PENDING. O colapso está no adapter Java, não no schema.
2. `ProviderCapabilityPort.ExecutionResult` é perfil de seguros (`items` / `quote`). Não cabe o resultado de giro sem extensão **autorizada** depois.
3. Geradores atuais do Spider (`preq-` + UUID, `spd-` + UUID, correlationId do envelope) cabem em 8–80 `[A-Za-z0-9_-]`.
4. Isolar este contrato **não** torna `SIMULATE_WORKING_CAPITAL` AVAILABLE nem executa o plano de 7 passos.

Pontos a fechar no item 1 (definição), sem implementar:

| Tema | Recomendação de analista | Estado |
|---|---|---|
| Numeração oficial | Não reutilizar `1.0`/`1.1` de seguros nem a série SAT `1.2`. Manter `credit-mock/0.1` só no mock até você nomear o perfil. | Aberto |
| purpose | `WORKING_CAPITAL_SIMULATION` no **provider**. Finalidade do satélite EXPERIENCE é outro item (hoje o Core só lista proteção). | Não misturar nesta fatia |
| scenarioKey | Concordar: fixture do test double; adapter/config, nunca UI. | Fechado na proposta, falta você confirmar |
| requestedAt | Deve ser UTC gerado na chamada; hoje o adapter de seguros usa instante fixo em 1.0. Mudança só no item 2, se autorizada. | Documentado |
| Mapeamento SAT | Não inventar status. PENDING/MISSING_CONTEXT do provider ≠ automaticamente `MISSING_CONTEXT` do satélite até o item da jornada. | Explicitado |

Nenhum arquivo de `spider/**` ou `mock-sistemas-credito/**` foi modificado nesta etapa.
