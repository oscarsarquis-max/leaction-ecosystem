# Plano CURSOR-028 — entregas verticais

**Ciclo:** CURSOR-028-A (especificação).  
**Regra:** evitar reescrita total; entregar fatias utilizáveis.  
**Fora de escopo global:** AWS, produção `panne` não migrada sem token, commit/push só com pedido explícito.

---

## Visão das fases

| ID | Nome | Dependência |
|---|---|---|
| **028-A** | Espinha dorsal (este pacote documental) | — |
| **028-B** | Página Fluxo produtivo + shell | A validado |
| **028-C** | Produto independente de receita | A |
| **028-D** | Recebimento por nota + histórico de preços | A (paralelo a C) |
| **028-E** | Sub-receitas e composição final | C (vínculo produto–receita) |
| **028-F** | Combos e modalidades de abastecimento | C |
| **028-G** | Ordem, ficha e impressões (cozinha/gestão/rótulo) | E (ideal); B |
| **028-H** | Custos, markup, margem, calculadora | C+D; F p/ combo |
| **028-I** | Validação integral por perfil | B…H |

---

## 028-B — Fluxo produtivo (navegação)

| | |
|---|---|
| **Objetivo** | `/fluxo` persistente; conectar telas existentes; estados comprováveis; voltar ao fluxo; redirect pós-login |
| **Entidades** | Nenhuma nova de domínio |
| **APIs** | Somente leituras existentes (contagens leves) |
| **Telas** | `FlowPage`; pin no `Shell`; `FlowTrail` central |
| **Migrations** | Não |
| **Compatibilidade** | Rotas atuais intactas; Quadro em `/producao` |
| **Testes** | Redirect; trilha; perfis; custos ocultos; teclado |
| **Riscos** | Confusão com “Fluxo por estado” do quadro — naming claro |
| **Demo** | Personas 026 percorrem steps |
| **Aceite** | Critérios em `NAVEGACAO-FLUXO-PRODUTIVO.md` |
| **Decisões incorporadas** | Vigência org+estabelecimento; TechnicalProduct→Produto; misto explícito; combo virtual; família org; intermediário=Produto |

## 028-C — Produto independente de receita

| | |
|---|---|
| **Objetivo** | Evoluir `TechnicalProduct` → Produto com CRUD sem receita; modalidades produced/purchased |
| **Entidades** | `TechnicalProduct` estendido (sem entidade concorrente) |
| **APIs** | `POST/GET/PATCH /products`; desacoplar `POST /recipes` de criar produto obrigatório |
| **Telas** | `/produtos`, detalhe; step 3 do Fluxo deixa de ser “em preparação” |
| **Migrations** | Sim — modalidade, unidades, família FK |
| **Compatibilidade** | Receitas existentes: backfill + link; OPs antigas intactas |
| **Testes** | Criar produto sem receita; purchased bloqueia OP |
| **Riscos** | Seed/demo que assume produto via receita |
| **Demo** | Suco engarrafado; Bolo/Pão/Coxinha como produtos |
| **Aceite** | Decisões 1–2, 9 do owner + decisões fechadas 028-B |

## 028-D — Recebimento por nota e histórico de preços

| | |
|---|---|
| **Objetivo** | Entrada de mercadorias por NF (manual/XML/scan/Fazenda preparada) com estoque só após confirmação humana |
| **Entidades** | `fiscal_inbound_*`, certificado (contrato), `supplier_item_link`; receipt nullable + `source=fiscal` |
| **APIs** | `/fiscal/documents*`, `/fiscal/access-keys/lookup`, `/fiscal/distribution/*` |
| **Telas** | `/gestao/compras/entradas`; Fluxo etapa 1 |
| **Migrations** | `0022_fiscal_inbound` (somente `panne_demo`) |
| **Fazenda** | Interface + adaptador + fixtures; `PANNE_FISCAL_LIVE=0` |
| **Aceite** | Ver [`entrada-fiscal-mercadorias.md`](entrada-fiscal-mercadorias.md) (modelo, Fazenda preparada/desativada, ativação/revogação) |

## 028-E — Sub-receitas e composição final

| | |
|---|---|
| **Objetivo** | Formulation referencia Formulation; exemplos bolo/coxinha |
| **Entidades** | Item de composição `sub_formulation_id`; anti-ciclo |
| **APIs** | Versions aceitam sub-receitas; custo/explode BOM |
| **Telas** | Editor de receita; árvore de composição |
| **Migrations** | Sim |
| **Compatibilidade** | role `preparation` legado: migrar ou mapear |
| **Testes** | Ciclo rejeitado; explode BOM; OP dependency opcional |
| **Riscos** | Ambiguity ingredient vs intermediate stock |
| **Demo** | Bolo (massa+cobertura); Coxinha (massa+recheio) |
| **Aceite** | Decisões 5–6; sem modelar combo como receita |

## 028-F — Combos e modalidades mistas

| | |
|---|---|
| **Objetivo** | Combo versionado; mixed buy/make |
| **Entidades** | `ProductComboVersion`, components; flags mixed |
| **APIs** | CRUD combo; disponibilidade; custo derivado |
| **Telas** | Detalhe combo; step Fluxo |
| **Migrations** | Sim |
| **Compatibilidade** | Sem impacto em OPs de produzidos |
| **Testes** | Combo sem receita; ciclo de componentes rejeitado; mixed com lote de origem |
| **Riscos** | Estoque FG/combo (decisão owner) |
| **Demo** | Combo café da manhã |
| **Aceite** | Decisões 3–4, 10; misto sem duplicar identidade |

## 028-G — Ordem, ficha e impressões

| | |
|---|---|
| **Objetivo** | OP a partir de produto produzido; OP direta de receita; prints kitchen/management/label |
| **Entidades** | FG lot mínimo (se aprovado); print profiles |
| **APIs** | create order from product; print serializers |
| **Telas** | Ordens; impressão; rotulagem alinhada |
| **Migrations** | Possível (FG) |
| **Compatibilidade** | Fluxo OP atual preservado |
| **Testes** | Purchased não cria OP; kitchen JSON sem money keys |
| **Riscos** | FG incompleto vs só good_units |
| **Demo** | Ficha bolo; rótulo; ficha gestão |
| **Aceite** | Decisões 7–8, 12; contratos em `IMPRESSOES-...` |

## 028-H — Custos, markup, margem, calculadora

| | |
|---|---|
| **Objetivo** | Precedência produto→família→org; calculadora lateral; memória |
| **Entidades** | Family (se aprovada); price rules levels |
| **APIs** | resolve markup; memory expand |
| **Telas** | Painel lateral contextual; preços |
| **Migrations** | Sim se família |
| **Compatibilidade** | formulas.py inalteradas na matemática base |
| **Testes** | Precedência; markup≠margem UI; combo margem |
| **Riscos** | Sobrepor regras 021 sem ADR |
| **Demo** | Cenário markup família vs produto |
| **Aceite** | Decisão 13; `PRECIFICACAO-E-CALCULADORA.md` |

## 028-I — Validação integral por perfil

| | |
|---|---|
| **Objetivo** | Smoke ponta a ponta por persona; matriz de permissões do Fluxo |
| **Entidades** | — |
| **APIs** | — |
| **Telas** | Checklist homologação |
| **Migrations** | Não |
| **Compatibilidade** | — |
| **Testes** | Smoke 028 + regressão 026 |
| **Riscos** | Demo drift |
| **Demo** | Atualizar manifesto cobertura |
| **Aceite** | Cada decisão 1–13 demonstrável; sem vazamento de custo na cozinha |

---

## Ordem sugerida de execução

```
028-A (validação owner)
   → 028-B
   → 028-C ⇄ 028-D (paralelo possível)
   → 028-E → 028-G
   → 028-F → 028-H
   → 028-I
```

## Fora deste plano (explícito)

- Canal de venda/PDV completo.
- PDF engine.
- Integração fiscal NF-e completa (além do necessário para histórico de preço).
- Alterar produção AWS / DB `panne` sem autorização.
