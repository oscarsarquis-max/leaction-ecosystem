# SPIDERBANK-ARQ-002 — Integração como Experience Satellite

**Status:** DRAFT — escopo revisado para implementação futura  
**Data:** 17 de setembro de 2026  
**Diretriz confirmada pelo usuário:** a relação Spider × SpiderBank deve seguir o mesmo processo do SegSense, outro satélite.  
**Efeito documental:** substitui o conector isolado como escopo principal proposto em SPIDERBANK-PRM-002. Não autoriza alterações no Core.

## 1. Relação arquitetural

SpiderBank será integrado ao Spider como Experience Satellite de crédito, seguindo o processo estrutural de integração do SegSense.

**Cliente → SpiderBank (frontend → BFF) → Satellite Contract → Spider → Capability Resolution → sistema provider de crédito → Spider → BFF SpiderBank → experiência do cliente.**

O endpoint de referência do satélite é `POST /v1/satellites/interactions`. A versão aplicável e o envelope serão confrontados com o contrato efetivamente implementado, preservando o comportamento do SegSense.

O satélite declara identidade, papel EXPERIENCE, objetivo confirmado, contexto permitido, finalidade, proveniência, correlação e classificação. Spider determina Intent canônico, políticas, plano, capabilities e executor.

## 2. O que seguir do SegSense

- Aplicação independente, frontend e BFF próprios.
- Identidade e credencial de satélite reconhecidas pelo Spider.
- Contexto governado e intenção confirmada pelo usuário.
- Integração pelo Satellite Contract, com autenticação, validação e correlação.
- Execução de capabilities mediada pelo Spider.
- Retorno de resultados e pendências pelo Spider para projeção na experiência.
- Separação física e lógica entre satélite e sistemas providers.
- Resultados ilustrativos explicitamente identificados no ambiente MOCK_ONLY.

Os detalhes de implementação serão verificados na referência atual antes de serem reutilizados. A diretriz não significa copiar schemas de seguros, finalidades de proteção, regras, produtos ou identidade visual.

## 3. Papel dos sistemas de crédito

Os sistemas da última coluna da imagem são os providers. O projeto `C:\Projetos\mock-sistemas-credito` representa esses executores em ambiente de teste; atualmente implementa apenas `SIMULATE_WORKING_CAPITAL`.

SpiderBank não chama a porta 8096, não seleciona provider, não recebe credencial do executor e não escolhe `scenarioKey`. Um conector HTTP dentro do Spider é apenas um componente técnico necessário à chamada do sistema escolhido pela resolução.

## 4. Correção do escopo anterior

A proposta de conector isolado não cobre, por si só, a relação Spider × SpiderBank solicitada. Ela poderá ser uma tarefa interna de implementação, mas não será considerada entrega suficiente da integração do satélite.

O escopo revisado deverá cobrir conjuntamente:

| Parte | Resultado necessário |
|---|---|
| Identidade do satélite | SpiderBank reconhecido como EXPERIENCE, com finalidade e permissões próprias de crédito. |
| Contexto e objetivo | Envelope válido, proveniência preservada e objetivo explicitamente confirmado. |
| Entrada no Spider | Recepção pelo mesmo processo contratual usado por SegSense, sem endpoint paralelo que contorne o Control Plane. |
| Interpretação, política e plano | Necessidade de crédito estruturada e execução determinada pelo Spider. |
| Capabilities e resolução | Reutilização do catálogo existente e seleção governada do sistema executor. |
| Integração com sistema | Contrato de crédito, autenticação e tratamento fiel dos estados do mock. |
| Retorno ao satélite | Resultado ou pendência traduzidos pela resposta contratual, com marcas de simulação preservadas. |
| Validação | Evidência ponta a ponta e regressão de seguros, não apenas teste do conector isolado. |

## 5. Questões que continuam explícitas

O plano existente `SEEK_WORKING_CAPITAL` possui outras capabilities indisponíveis. Habilitar `SIMULATE_WORKING_CAPITAL` não permite pular pré-requisitos silenciosamente. A fatia executável deverá ser definida e autorizada, indicando quais etapas existem e quais permanecem indisponíveis.

A digitação de contexto no SpiderBank deve seguir o mecanismo governado aceito pelo contrato. Persistir texto no BFF não basta para torná-lo evidência governada. O processo atual do SegSense será a referência a inspecionar.

As finalidades do satélite e do executor têm responsabilidades distintas. `WORKING_CAPITAL_SIMULATION` permanece a recomendação para o provider; não é automaticamente a finalidade de todo o satélite.

A versão local `credit-mock/0.1` não será apresentada como versão oficial do Spider. A numeração oficial continua pendente de definição.

## 6. Critério de conclusão da integração futura

A integração somente será considerada concluída quando uma interação do SpiderBank percorrer o Satellite Contract, a governança e a resolução do Spider, alcançar o mock por capability autorizada e retornar um resultado fiel ao satélite. Falta de contexto, recusa sintética, pendência e indisponibilidade devem preservar suas diferenças, sem fabricar aprovação ou encaminhamento humano real.

Quando pré-requisitos impedirem a execução, o resultado correto será o impedimento explícito. Um resultado de teste obtido por chamada direta ao mock não prova a jornada do satélite.

## 7. Autorização e documentação

A diretriz arquitetural deste documento foi explicitamente determinada pelo usuário. A implementação do satélite e as alterações no Spider continuam sujeitas à autorização específica, com arquivos, escopo e critérios reunidos em um pacote revisado.

O ADR principal permanece DRAFT. Nesta etapa foram atualizados apenas documentos da conversa. Nenhum código, configuração, catálogo ou teste do monorepo foi alterado.

---

## Análise desta conversa (17 set 2026) — inspeção, sem alterar Core/mock

### O que o documento substitui

Não existe arquivo `SPIDERBANK-PRM-002.md` em `spider-bank/documents/`. O conector isolado estava em **PRM-001 §5** (adapter HTTP, YAML, capability AVAILABLE). Este ARQ-002 passa a ser o escopo principal da relação Spider × SpiderBank. CONTRACT-001 permanece o perfil **Spider ↔ executor**. Os dois são complementares.

### Processo SegSense verificado no repositório

O BFF SegSense (`HttpDemoProtectionDecisionAdapter`) chama exatamente:

- `POST {spiderBaseUrl}/v1/satellites/interactions`
- identidade `X-Spider-Satellite-Id` (`segsense`)
- credencial `X-Spider-Satellite-Secret` (fora do frontend)
- `X-Correlation-ID` e `Idempotency-Key`

O Control Plane registra o satélite em `application-local-demo.yml` (`role: EXPERIENCE`, purpose `INSURANCE_PROTECTION_ASSESSMENT`, objetivos e `governed-context-ids` de proteção). `DemoSliceRules` só encaminha temas de seguros/agro/cotação residencial. O README em `segsense/services/spider-integration/` está desatualizado (ainda diz contrato ausente); a referência operacional é o adapter acima e `SPIDER-SATELLITE-CONTRACT-V1.md`.

Copiar o **processo** não copia purpose, objetivos, sourceIds `SEGSENSE_*`, `SEGSENSE_URL_`, schemas 1.1/1.2 de cotação nem visual.

### Caminho paralelo que este ARQ exclui como integração

Já existem no Core, fora do Satellite Contract:

- `GET /v1/demo/spiderbank/entry`
- `POST /v1/demo/spiderbank/understand`

Esses endpoints de Contextual Link / `DIRECT_ENTRY` não são o processo SegSense. Pelo item 4, **não** constituem a relação Spider × SpiderBank. Não foram alterados nesta etapa.

### Tensão de contexto (já no ADR 0.4)

SAT-003 1.0 EXPERIENCE exige `SATELLITE_GOVERNED` + `trustLevel=GOVERNED` + `captureMethod=SERVER_REGISTRY` e `sourceId` listado no registry. `DIRECT_ENTRY` e texto só no BFF **não** são prova governada. A série 1.1 admite contribuição `USER_DECLARED` **além** da fonte governada; 1.2 de URL é específica do SegSense (`SEGSENSE_URL_`). A fatia de crédito precisa de mecanismo próprio, ainda sem copiar esses IDs.

### Plano e capability

`SEEK_WORKING_CAPITAL` / `WORKING_CAPITAL_DIAGNOSTIC_V1` tem 7 passos, todos `NOT_AVAILABLE` no catálogo, inclusive `SIMULATE_WORKING_CAPITAL`. Habilitar só a simulação, sem fatia autorizada, deixaria o plano bloqueado nos pré-requisitos — e o resultado correto seria o impedimento explícito.

### Relação com os outros DRAFTs

| Documento | Papel | Efeito deste ARQ |
|---|---|---|
| ADR-001 | Produto e fronteiras | Continua DRAFT. A diretriz de satélite já estava lá; este texto fecha o *como* da integração. |
| CONTRACT-001 | Pedido/resposta do executor | Permanece item 1 do perfil de crédito. Não substitui o satélite. |
| PRM-001 | Lacunas do mock vs adapter atual | Continua mapa técnico. O conector vira subtarefa, não entrega. |

### O que ainda precisa da sua palavra (documento, não código)

1. Aceitar este ARQ-002 como escopo da integração (SAT-003, não conector isolado, não `/v1/demo/spiderbank/*`).
2. Definir a **fatia executável** do plano de 7 passos: o que permanece indisponível de forma explícita.
3. Nomear a **finalidade do satélite** EXPERIENCE (distinta de `WORKING_CAPITAL_SIMULATION` no provider).
4. Escolher, na inspeção da jornada, a versão SAT aplicável (1.0 vs 1.1 com `USER_DECLARED`) — sem reutilizar 1.2 de URL do SegSense.

Nenhum arquivo de `spider/**` ou `mock-sistemas-credito/**` foi modificado nesta etapa.
