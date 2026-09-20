# SPIDERBANK-MOCK-001 — Mock de Sistemas de Crédito

**Data:** 17 de setembro de 2026; ampliado em 18 de setembro de 2026  
**Status documental:** local de teste — `credit-mock/0.1` (passo 6) e `credit-mock/0.2` (passos 2–5)  
**Implementação:** mock isolado na primeira entrega; a segunda entrega registra o mesmo executor no recorte demonstrativo do Spider. Não constitui aprovação do ADR geral nem contrato oficial de produção.  
**Fronteiras:** TEST DOUBLE / ILLUSTRATIVE / MOCK_ONLY / SIMULATED_INFRASTRUCTURE.

## Modelo arquitetural confirmado

Na imagem, a barra verde representa Spider; as colunas representam fases do crédito; seus blocos representam subdomínios; a última coluna representa os sistemas que serão providers de crédito. A parte inferior é desconsiderada.

Um provider corresponde ao papel de executor de um sistema, podendo atender uma ou mais capabilities. Spider estrutura, governa e compõe a execução. O mock desta fatia representa um desses sistemas, responsável somente por uma simulação de capital de giro. Não atribui funções a identificadores específicos da imagem sem levantamento adicional.

Destino escolhido: `C:\Projetos\mock-sistemas-credito`, aplicação independente do satélite `C:\Projetos\spider-bank`, seguindo a separação observada entre SegSense e seu provider mock.

## Inspeção e compatibilidade

HEAD observado: `5ee7756`, branch `feat/spider-sat-003-segsense`, com alterações locais no Spider e no mock de seguros. Esses arquivos foram preservados.

O catálogo `StaticBusinessCapabilityCatalog` contém `SIMULATE_WORKING_CAPITAL` como `NOT_AVAILABLE`. Não foi criado identificador duplicado de capability.

Os schemas de provider inspecionados restringem finalidade e inputs ao domínio de seguros. O adapter HTTP atual também verifica a identidade `insurance-provider-mock` e possui projeções de seguros. Portanto, este serviço não é compatível ponta a ponta com o adapter atual. Usa envelope semelhante, mas contrato local explícito `credit-mock/0.1`.

## Interface

- `GET /health`: identificação, fronteira simulada, `processUp`, capabilities suportadas, `integratedWithSpider: false` e `chainReadiness: determined_by_spider`. Sem dados de pedidos. O flag **não** prova integração com a Spider.
- `POST /v1/provider/capabilities/{capabilityId}/executions` para `GET_CUSTOMER_PROFILE`, `CHECK_CUSTOMER_REGISTRATION`, `GET_CREDIT_PROFILE`, `FIND_ELIGIBLE_PRODUCTS` (`credit-mock/0.2`, finalidade `WORKING_CAPITAL_ASSESSMENT`, inputs `scenarioKey` + `subjectRef`) e `SIMULATE_WORKING_CAPITAL` (`credit-mock/0.1`).
- Autenticação: `X-Credit-Mock-Credential`, configurada por variável de ambiente; comparação por hash em tempo constante.
- Tipo de conteúdo: JSON; corpo limitado a 8.192 bytes, inclusive durante leitura HTTP.
- Respostas não são armazenáveis em cache. Sem CORS habilitado, callbacks, chamadas externas ou persistência.

## Pedido

Campos obrigatórios:

| Campo | Regra |
|---|---|
| contractVersion | `credit-mock/0.1` |
| requestId, correlationId, decisionId | 8–80 caracteres ASCII: letras, números, hífen ou underscore |
| capabilityId | `SIMULATE_WORKING_CAPITAL` |
| capabilityVersion | `1.0` local, sujeita a alinhamento contratual futuro |
| purpose | `WORKING_CAPITAL_SIMULATION`, finalidade local proposta |
| dataClassification | PUBLIC ou INTERNAL; somente dados sintéticos |
| requestedAt | Data/hora UTC com segundos, opcionalmente milissegundos |
| inputs | Objeto com scenarioKey e, quando disponíveis, principalCents e termMonths |

`callback` é opcional e deve ser nulo. Campos extras são rejeitados em todo o envelope e em inputs. Não são aceitos nome, documento de cliente, contexto integral, objetivo, plano ou taxas impostas pelo chamador.

`principalCents` aceita inteiro de 10.000 a 100.000.000; `termMonths`, inteiro de 1 a 36. Esses limites são exclusivos do teste. Ausência gera pendência, enquanto valores inválidos geram erro de payload.

## Cenários determinísticos

| scenarioKey | Resultado |
|---|---|
| SUCCESS | COMPLETED com cálculo sintético, quando os dois valores necessários estão presentes |
| MISSING_CONTEXT | PENDING, motivo MISSING_CONTEXT e campos faltantes; quando forçado com valores completos, solicita syntheticSupportingContext |
| REJECTED | REJECTED com motivo SYNTHETIC_SCENARIO_REJECTED; não representa Policy/Guard do Spider |
| HUMAN_REVIEW | PENDING com motivo SYNTHETIC_HUMAN_REVIEW; reviewQueued=false, sem fila humana real |
| UNAVAILABLE | HTTP 503, PROVIDER_UNAVAILABLE, retryable=true |

Ausência de valor ou prazo precede a execução de cenários de recusa/análise humana. Cenários são fixtures de teste, não regras de elegibilidade, risco ou decisões sobre clientes.

Cálculo fictício: juros simples com constante mensal de 100 pontos-base (1%), aplicada ao principal por todo o prazo. Juros arredondados em centavos; total distribuído em parcelas inteiras, com diferença de arredondamento distribuída nas primeiras parcelas. Não corresponde a Price ou SAC. Não inclui IOF, tarifas, CET, garantias, carência ou calibração de mercado.

Exemplo sintético: principal de 1.000.000 centavos por 12 meses → juros de 120.000 centavos → total de 1.120.000 centavos. Não é condição financeira disponível.

Todo resultado de domínio contém `testDouble: true`, `MOCK_ONLY`, `NON_BINDING_DEMO`, `offerable: false` e aviso de ausência de valor comercial. Não há produto, aprovação, proposta, contratação ou desembolso.

## Correlação e erros

O resultado preserva requestId e correlationId e identifica capability e provider. providerReference é um hash determinístico do pedido serializado; não representa idempotência persistente. executedAt varia por execução, enquanto o cálculo é repetível.

Erros HTTP: 400 payload/capability inválidos, 401 credencial inválida, 404 rota inexistente, 413 tamanho excedido, 415 tipo de conteúdo inválido e 503 indisponibilidade simulada. Erros não refletem o corpo enviado.

## Verificação

Seis testes automatizados passaram na cópia preparada: cálculo e soma exata de parcelas; cenários sem condições inventadas; informações ausentes; autenticação e capability; entradas inválidas e minimização; teste HTTP real em loopback com headers e limite de corpo.

## Histórico da primeira entrega (não apagar)

Na primeira entrega o mock existia isolado: não havia adapter de crédito no Spider, o catálogo permanecia `NOT_AVAILABLE` por omissão e `integratedWithSpider` era `false` porque não havia cadeia. Essa evidência permanece válida como histórico.

A segunda entrega (SPIDERBANK-ARQ-004) registra `credit-provider-mock` no recorte `local-demo`, com schemas locais 0.1/0.2. A prontidão da cadeia continua sendo determinada no Spider. Este documento não publica contrato oficial de produção.

O ADR principal permanece DRAFT quanto a crédito real. Não há bureaus, documentos pessoais, instituições financeiras, aprovação, contratação ou desembolso.

## Denominação definida pelo usuário

Nome: **Mock de Sistemas de Crédito**. O projeto representa sistemas no papel de providers. A primeira fatia implementa apenas SIMULATE_WORKING_CAPITAL; o nome plural não significa que vários sistemas já estejam implementados. O identificador técnico credit-provider-mock foi preservado nesta revisão de nomenclatura.
