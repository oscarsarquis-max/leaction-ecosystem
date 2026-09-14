# SEGSENSE_FUN_004 — Intenção livre, perguntas e cotação sintética

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_FUN_004 |
| Título | Intenção livre, perguntas de complemento e contrato de cotação sintética |
| Categoria | FUN — fundamentos |
| Versão | 1.0 |
| Status | Vigente nesta etapa; **não** é cotação Icatu nem oferta vinculante |
| Data | 14/09/2026 |

Complementa `SEGSENSE_FUN_003` (possibilidades ilustrativas). A jornada pública desta etapa classifica texto livre; a jornada ilustrativa permanece íntegra via API e quando o texto mapeia “entender opções” / “comparar”.

## 1. Matriz (não começa no frontend)

| Contexto e fonte | Intenção capturada | Dados faltantes | Decisão Spider | Capability | Inputs mínimos do provider | Cálculo mock | Cotação exibida |
|---|---|---|---|---|---|---|---|
| Relato “Houve incêndios nas proximidades” (`USER_DECLARED` / `SEGSENSE_DECLARED_NEARBY_FIRES_V1`) | Texto “Quero contratar um seguro residencial” → `SIMULATE_HOME_QUOTE` | `dwelling_type`, `insured_amount`, `cover_period` | `MISSING_CONTEXT` + `PROVIDE_CONTEXT` | nenhuma | — | não ocorre | perguntas humanas; sem R$ |
| URL governada `/demonstracao/fontes/proximidade-incendios` (`SATELLITE_GOVERNED` / `SEGSENSE_NEARBY_FIRES_SYNTHETIC_V1`) | mesma intenção, após correção explícita | os três campos acima se ausentes | igual | nenhuma | — | não ocorre | o artigo **não** prova risco do imóvel e **não** agrava prêmio |
| Incêndios + intenção residencial + apartamento + R$ 300.000 + 12 meses | `SIMULATE_HOME_QUOTE` confirmada pelo botão “Gerar cotação simulada” | nenhum obrigatório | `READY` | `GENERATE_SYNTHETIC_HOME_QUOTE` | `scenarioKey`, `dwellingType=APARTMENT`, `insuredAmountCents=30000000`, `coverPeriodMonths=12`, `ratingRuleVersion=HOME_QUOTE_SYNTHETIC_V1` | `premiumAnnualCents = round_half_up(30000000 × 18 / 10000) = 54000` | **R$ 540,00** após `COMPLETED` + `quoteReference` |
| Mesmo capital, casa | idem | nenhum | `READY` | mesma | `dwellingType=HOUSE` | 22 bps → **66000** centavos | R$ 660,00 |
| Capital R$ 600.000, apartamento | idem | nenhum | `READY` | mesma | `60000000` | **108000** | R$ 1.080,00 |
| Fonte de incêndios + “entender opções ilustrativas” | `UNDERSTAND_PROTECTION_OPTIONS` | `home_intention` | `MISSING_CONTEXT` | nenhuma | — | não ocorre | pergunta se deseja avaliar proteção residencial |
| Continuidade familiar + entender opções | `UNDERSTAND_PROTECTION_OPTIONS` | nenhum desta fatia | `READY` | `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO` (Provider 1.0) | só `scenarioKey` | itens ilustrativos, sem R$ | possibilidades ilustrativas (jornada antiga íntegra) |
| “quero pagar agora” / emitir apólice | `REQUEST_EFFECTIVE_CONTRACT` | — | **não chama Spider** | — | — | — | recusa local: simulação ≠ contratação |
| Sem contexto | qualquer | `theme` | BFF `MISSING_CONTEXT` sem Spider | — | — | — | “descreva um contexto…” |
| Provider down após dados suficientes | `SIMULATE_HOME_QUOTE` | nenhum | `PROVIDER_UNAVAILABLE` | despachada, sem `COMPLETED` | enviados | não há prêmio desta execução | sem valor antigo, sem fallback |

O clique no artigo **não** é intenção. O texto original do relato **não** atravessa a fronteira; só tema estruturado e atributos de cotação (tipo, capital em centavos, período).

## 2. Classificação limitada no SegSense

| Texto (exemplos) | Código | Interpretação mostrada |
|---|---|---|
| “Quero contratar um seguro residencial” | `SIMULATE_HOME_QUOTE` | Entendi que você quer avaliar uma proteção residencial. |
| “entender opções ilustrativas…” | `UNDERSTAND_PROTECTION_OPTIONS` | Entendi que você quer entender opções ilustrativas de proteção. |
| “comparar lacunas…” | `COMPARE_COVERAGE_GAPS` | Entendi que você quer comparar opções ilustrativas deste contexto. |
| “pagar agora”, “emitir apólice”, “assinar contrato” | `REQUEST_EFFECTIVE_CONTRACT` | Contratar de verdade depende de seguradora e produto autorizados. |
| vazio / não reconhecido | `UNRECOGNIZED` | Não reconheci o que você deseja. Sem default. |

A pessoa corrige o texto antes do botão. O botão da fatia residencial é **Gerar cotação simulada**. Frase pré-ação: “Vamos calcular uma simulação; contratar de verdade depende de seguradora e produto autorizados.”

## 3. Regra `HOME_QUOTE_SYNTHETIC_V1`

Inventada para demonstrar o software. **Não** é tarifa de mercado, atuarial nem da Icatu. Incêndios na fonte editorial **não** entram na conta.

```
premiumAnnualCents = round_half_up(insuredAmountCents * dwellingBps / 10000)
APARTMENT: 18 bps
HOUSE:     22 bps
período: somente 12 meses
mínimo: R$ 50.000 (5_000_000 centavos)
máximo: R$ 2.000.000 (200_000_000 centavos)
```

`round_half_up`: quociente inteiro; se o resto × 2 ≥ denominador, soma 1.

Exemplo reproduzível: apartamento, capital R$ 300.000 → 30_000_000 × 18 / 10_000 = 54_000 centavos = **R$ 540,00**.

Campos do resultado: `insuredAmountCents`, `premiumAnnualCents`, `coverPeriodMonths`, `dwellingType`, `dwellingBps`, `ratingRuleVersion`, `quoteReference` (`providerReference`), `calculatedAt`, `premises`, origem `NON_BINDING_DEMO`, status `NON_BINDING_DEMO`. Sem parcelamento, impostos, franquia (não há regra de franquia nesta versão) nem elegibilidade real.

## 4. Contratos

| Contrato | Uso nesta etapa |
|---|---|
| Satellite 1.0 | Rota legado rotulada; atributos ≤ 8; sem mudança silenciosa |
| Satellite 1.1 | Fluxo público: contribuições, `SIMULATE_HOME_QUOTE`, atributos de cotação (capital **não** está no YAML de allowlist; valor livre na faixa validada) |
| Provider 1.0 | `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO`; só `inputs.scenarioKey` |
| Provider 1.1 | `GENERATE_SYNTHETIC_HOME_QUOTE`; inputs numéricos; **não** concatenar prêmio em `scenarioKey` |

SegSense **não** chama o mock. Spider despacha só depois de `READY`.

## 5. Fontes oficiais consultadas (linguagem; sem produto Icatu residencial)

| Fonte | O que foi usado | O que **não** foi verificado |
|---|---|---|
| SUSEP — informações para escolha de seguro | Distinguir informação, simulação e contratação | API/produto Icatu residencial |
| Institucional Icatu (vida, previdência, capitalização) | Não rotular a simulação residencial como oferta Icatu | Contrato/API de seguro residencial autorizado pela Icatu — **ausente** |

SHA do PNG oficial (PRM_018, intacto): `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D`.
