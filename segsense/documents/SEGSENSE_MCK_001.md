# SEGSENSE_MCK_001 — Contrato conceitual do Insurance Provider Mock

## Controle

| Campo | Valor |
|---|---|
| Identificador | SEGSENSE_MCK_001 |
| Versão | 1.0 |
| Data | 12/09/2026 |
| Natureza | Especificação **não executável** |
| Status | Conceitual; camada A executada no PRM_013 como aplicação irmã, sem APIs Icatu |

A redação original (PRM_012) era não executável. O PRM_013 criou a aplicação irmã `segsense-provider-mock/` (camada A), sem APIs Icatu, sem preço e sem chamada SegSense→mock.

O envelope didático abaixo é `ILLUSTRATIVE_NOT_ICATU_CONTRACT`. Não alega equivalência com APIs reais.

## Independência física

| Aplicação | Papel |
|---|---|
| SegSense | Experiência e contextualização |
| Spider | Interpretação / decisão / execução **somente** com Satellite Contract externo |
| Insurance Provider Mock | Outro processo, repositório, runtime, configuração, dados sintéticos e ciclo de vida |

O mock **não** fica dentro da Spider nem do SegSense. O SegSense **não** contorna a Spider ligando-se ao mock. A camada A passou a ter runtime irmão no PRM_013 (`segsense-provider-mock/`); MCK_001 permanece a especificação conceitual, sem APIs Icatu.

## Camada A — envelope didático

Capacidade futura (abstrata): receber um pedido de **ilustração** de jornada de proteção e devolver um resultado **explícito de simulação**.

| Campo | Valor |
|---|---|
| Input abstrato | Identificador de cenário ilustrativo; objetivo declarado; sem PII |
| Output abstrato | Estado `ILLUSTRATIVE`; texto de não oficialidade; sem preço |
| Origem da evidência | Nenhuma API Icatu verificada |
| Responsável pela decisão | Aplicação mock (não a Icatu; não o SegSense) |
| Verificação | Bloqueada até PRM_013 + evidência |
| Erro / indisponibilidade | Falha explícita; nunca “cotação indisponível da Icatu” |
| Dados mínimos | NON_PERSONAL; sintéticos |
| Versão | `mck-envelope-v0` (conceitual) |
| Fronteira de segurança | Sem credencial Icatu; sem PII; deny-by-default no futuro runtime |

## Camada B — mapeamento Icatu

| Operação / campo Icatu | Evidência | Estado |
|---|---|---|
| Qualquer endpoint, schema, payload ou nome de API | Catálogo público sem especificação (`SEGSENSE_SRC_002`) | **BLOQUEADO** |
| Produto, cobertura, prêmio, apólice | Marketing institucional ≠ contrato | **BLOQUEADO** |

Não há fluxo feliz operacional desenhado.

## Alternativas futuras (não aprovadas)

1. Spider chama o mock após contrato satélite — única direção compatível com `SEGSENSE_ADR_001`.
2. SegSense chama o mock — **rejeitada** (integração operacional direta).
3. Mock dentro do SegSense ou da Spider — **rejeitada**.

## Pré-condições para PRM_013

1. Aprovação formal do PRM_012.
2. Pelo menos um artefato oficial acessível (schema/exemplo) **ou** decisão explícita de permanecer só na camada A.
3. Sem preencher lacunas com nomes inventados de API Icatu.

## Critérios de parada

Parar PRM_013 se: não houver contrato/evidência; pedido de “sandbox Icatu”; exigência de preço/produto/cobertura simulados como se fossem da Icatu; ou tentativa de client HTTP no SegSense.
