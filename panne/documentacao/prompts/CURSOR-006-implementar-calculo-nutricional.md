# CURSOR-006 — Implementar o cálculo nutricional determinístico

## Objetivo

Implemente o cálculo nutricional bruto, determinístico, versionado e rastreável da Panne.

O cálculo deverá partir exclusivamente de:

- uma `FormulationVersion`;
- seus `FormulationItem`;
- as `IngredientVersion` referenciadas;
- os nutrientes associados a essas versões;
- parâmetros técnicos explícitos de rendimento e porção.

## Limite regulatório obrigatório

O resultado deste ciclo não é um rótulo e não pode ser apresentado como conforme.

Não implemente ainda:

- arredondamento regulatório definitivo;
- percentual de valor diário;
- definição de porção legal;
- rotulagem nutricional frontal;
- alegações nutricionais;
- declarações normativas de alergênicos;
- declarações de glúten ou lactose;
- layout oficial da tabela;
- PDF;
- aprovação regulatória.

Use nomes como:

- cálculo nutricional técnico;
- resultado bruto;
- prévia técnica;
- incompleto;
- não validado regulatoriamente.

Não use “rótulo aprovado” ou “conforme Anvisa”.

## Proteção do legado

Não acesse o MySQL legado.

Não use credenciais, DDL ou dados da origem neste ciclo.

Toda operação de banco deve ocorrer exclusivamente no PostgreSQL local da Panne.

Confirme antes das migrações:

- PostgreSQL;
- banco lógico `panne`;
- ambiente local ou teste;
- head inicial `0004_formulation_lab`.

## Migração

Crie:

```text
0005_nutrition_calculation
```

Tabelas:

1. `nutrition_calculation`
2. `nutrition_calculation_item`
3. `calculation_evidence`

## `nutrition_calculation`

Representa um snapshot imutável de cálculo nutricional.

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `status`;
- `calculation_basis`;
- `formula_net_mass_g`;
- `expected_final_mass_g`, quando disponível;
- `portion_mass_g`, quando informada;
- `algorithm_name`;
- `algorithm_version`;
- `rounding_policy`;
- `calculated_at`;
- `calculated_by_user_id`, quando disponível;
- `warnings`;
- `assumptions`.

Estados:

- `complete`;
- `incomplete`;
- `invalidated`.

Bases iniciais:

- `whole_formula`;
- `per_100g`;
- `technical_portion`.

Requisitos:

- snapshot append-only;
- sem atualização da composição calculada;
- invalidação por novo evento ou estado, sem apagar o cálculo;
- apontar para uma versão específica de formulação;
- preservar algoritmo e versão;
- não depender da versão “atual” dos ingredientes depois do cálculo.

## Massa final

O cálculo nutricional total deve usar a massa líquida incorporada à formulação.

Para valores por 100 g do produto final, utilize massa final explícita.

Quando `expected_bake_loss_rate` estiver disponível:

```text
expected_final_mass =
    formula_net_mass × (1 - expected_bake_loss_rate)
```

Requisitos:

- taxa entre 0 e menor que 1;
- massa final positiva;
- registrar que a perda de massa não significa perda automática proporcional de nutrientes;
- na ausência de fatores de retenção, preservar o total de nutrientes e alterar somente sua concentração pela massa final;
- registrar essa hipótese como evidência;
- não inventar fatores de retenção.

Se não houver massa final ou perda válida, o cálculo total pode existir, mas o resultado por 100 g do produto final deve ficar incompleto.

## Contribuição nutricional dos ingredientes

Cada `IngredientVersion` possui base explícita `per_100g`.

Para cada nutriente disponível:

```text
ingredient_contribution =
    formulation_item_net_mass_g
    × ingredient_nutrient_amount
    ÷ 100
```

Total da formulação:

```text
formula_nutrient_total =
    soma das contribuições dos ingredientes
```

Valor por 100 g do produto final:

```text
nutrient_per_100g_final =
    formula_nutrient_total
    ÷ expected_final_mass_g
    × 100
```

Valor por porção técnica:

```text
nutrient_per_portion =
    nutrient_per_100g_final
    × portion_mass_g
    ÷ 100
```

Use exclusivamente `Decimal`.

Não use `float`.

Não aplique arredondamento regulatório. Preserve precisão interna e registre política técnica de apresentação separadamente.

## Dados ausentes

Dado nutricional ausente não é zero.

Se uma versão de ingrediente não possuir determinado nutriente:

- registre ausência;
- identifique ingrediente e versão;
- marque o nutriente afetado como incompleto;
- marque o cálculo como `incomplete` quando a ausência impedir conclusão;
- não substitua por zero;
- não peça à IA para preencher;
- não use dados de outra versão silenciosamente.

Diferencie:

- valor conhecido igual a zero;
- valor desconhecido;
- nutriente não aplicável;
- valor abaixo do limite de quantificação, apenas quando a fonte informar isso.

## `nutrition_calculation_item`

Cada linha representa o total calculado de um nutriente.

Campos mínimos:

- `id`;
- `organization_id`;
- `nutrition_calculation_id`;
- `nutrient_definition_id`;
- `measurement_unit_id`;
- `whole_formula_amount`;
- `per_100g_amount`, quando calculável;
- `technical_portion_amount`, quando calculável;
- `completeness_status`;
- `created_at`.

Estados de completude:

- `complete`;
- `missing_data`;
- `not_applicable`;
- `below_quantification_limit`.

Requisitos:

- unicidade entre cálculo e nutriente;
- valores não negativos;
- unidade compatível com a definição do nutriente;
- nenhuma coluna de `%VD`;
- nenhuma representação em texto como fonte numérica.

## `calculation_evidence`

Registre a memória de cálculo por ingrediente e nutriente.

Campos mínimos:

- `id`;
- `organization_id`;
- `nutrition_calculation_id`;
- `nutrition_calculation_item_id`, quando existir;
- `formulation_item_id`;
- `ingredient_version_id`;
- `ingredient_nutrient_id`, quando existir;
- `data_source_id`, quando existir;
- `evidence_type`;
- quantidade do ingrediente utilizada;
- valor nutricional de origem;
- base do valor;
- contribuição calculada;
- status;
- mensagem técnica;
- `created_at`.

Tipos de evidência:

- `source_value`;
- `calculated_contribution`;
- `missing_value`;
- `yield_assumption`;
- `portion_assumption`;
- `unit_conversion`;
- `warning`.

Requisitos:

- nenhuma credencial;
- nenhuma saída de IA;
- rastreabilidade até versão do ingrediente e fonte;
- evidência imutável;
- capacidade de reconstruir o cálculo.

## Ingredientes compostos e preparações

Use os dados nutricionais publicados da `IngredientVersion` referenciada.

Não recalcule recursivamente uma composição se a versão já possuir dossiê nutricional aprovado como fonte do cálculo.

Se uma preparação não possuir dados nutricionais publicados:

- marque o resultado como incompleto;
- não percorra silenciosamente formulações externas;
- registre a ausência.

A estratégia de publicação de formulação como ingrediente continuará fora deste ciclo.

## Açúcares, energia e nutrientes derivados

Não derive automaticamente:

- energia por fatores de Atwater;
- açúcares adicionados;
- gorduras totais por soma parcial;
- carboidratos por diferença;
- sódio a partir de sal;
- lactose;
- glúten.

Essas derivações exigirão regras técnicas e regulatórias versionadas.

Se o nutriente existir com valor e fonte na versão do ingrediente, ele pode ser agregado normalmente.

## Unidades

Implemente conversões somente quando:

- declaradas no catálogo;
- dimensionalmente compatíveis;
- determinísticas;
- acompanhadas de evidência.

Não converta massa e volume sem fator específico e aprovado.

Rejeite unidade incompatível.

## Estado da formulação

Permita cálculo para:

- versão `draft`, identificado como simulação;
- versão `published`, identificado como cálculo de versão publicada.

O status da formulação deve aparecer no snapshot.

Nenhum cálculo de rascunho pode ser apresentado como aprovado.

## Imutabilidade

Garanta:

- cálculo persistido imutável;
- itens imutáveis;
- evidências imutáveis;
- ausência de atualização destrutiva;
- novo cálculo quando entradas, algoritmo ou parâmetros mudarem;
- cálculos anteriores preservados.

## Motor de domínio

Implemente o motor fora da API e sem dependência de:

- HTTP;
- frontend;
- LLM;
- Bedrock;
- serviços externos.

Separe:

- validação das entradas;
- agregação;
- normalização de unidades;
- completude;
- evidências;
- persistência do snapshot.

## Testes obrigatórios

Use PostgreSQL real e Python 3.12.

### Migração

- `0004` → `0005`;
- downgrade para `0004`;
- novo upgrade;
- criação de `0001` até head.

### Cálculo

- ingrediente único;
- múltiplos ingredientes;
- múltiplos nutrientes;
- valor conhecido igual a zero;
- valor desconhecido;
- cálculo total;
- cálculo por 100 g;
- cálculo por porção técnica;
- perda de forno zero;
- perda válida;
- perda inválida;
- massa final ausente;
- ingrediente composto com dados publicados;
- preparação sem dados;
- unidade incompatível;
- precisão decimal;
- reconstrução pelas evidências.

### Isolamento

- formulação e ingredientes na mesma organização;
- tentativa entre organizações rejeitada;
- cálculo de outra organização inacessível pela camada normal.

### Imutabilidade

- cálculo não atualizável;
- item não atualizável;
- evidência não atualizável;
- invalidação preserva histórico;
- novo cálculo não altera o anterior.

### Limites regulatórios

Teste que o domínio não gera:

- `%VD`;
- lupa frontal;
- alegação nutricional;
- texto de conformidade;
- declaração automática de glúten, lactose ou alergênicos.

## Endpoints

Não crie CRUD.

Não exponha cálculos por HTTP neste ciclo.

Mantenha somente:

- `/health`;
- `/ready`.

## Documentação

Registre:

- fórmulas;
- precisão;
- hipóteses;
- tratamento de perdas;
- dados ausentes;
- completude;
- unidades;
- ingredientes compostos;
- imutabilidade;
- evidências;
- limites regulatórios;
- diagrama Mermaid;
- migração;
- testes;
- riscos.

Inclua referências oficiais apenas como contexto arquitetural:

- RDC 429/2020;
- IN 75/2020;
- RDC 727/2022;
- perguntas e respostas atuais da Anvisa.

Não transcreva extensamente as normas e não implemente suas regras neste ciclo.

Registre este prompt em `documentacao/prompts/`.

Registre o retorno em `documentacao/retornos/`.

## Restrições

- Não acessar o MySQL.
- Não criar rótulo.
- Não gerar PDF.
- Não implementar conformidade.
- Não calcular `%VD`.
- Não decidir porção legal.
- Não criar rotulagem frontal.
- Não implementar alergênicos normativos.
- Não integrar IA.
- Não alterar frontend.
- Não criar CRUD.
- Não inserir dados reais.
- Não criar seeds sem fonte.
- Não alterar outras aplicações.
- Não fazer commit, push ou deploy.

## Critérios de aceite

- migração `0005` reversível;
- cálculo derivado exclusivamente da formulação versionada;
- valores por fórmula, 100 g e porção técnica;
- dados ausentes distintos de zero;
- massa final e perda tratadas explicitamente;
- evidências reconstruíveis;
- precisão decimal;
- snapshots imutáveis;
- isolamento multiempresa;
- ausência de regras regulatórias antecipadas;
- testes em PostgreSQL e Python 3.12;
- nenhuma credencial;
- nenhuma alteração no legado.

## Retorno obrigatório

Entregue:

1. confirmação de que o MySQL não foi acessado;
2. validação do PostgreSQL alvo;
3. arquivos criados e alterados;
4. tabelas e restrições;
5. fórmulas implementadas;
6. tratamento da massa final;
7. tratamento de dados ausentes;
8. tratamento de compostos e preparações;
9. unidades e conversões;
10. política de precisão;
11. estrutura de evidências;
12. imutabilidade;
13. upgrade, downgrade e reaplicação;
14. testes e resultados;
15. execução em Python 3.12;
16. confirmação de ausência de regras regulatórias;
17. `git diff --stat` e `git status --short`;
18. riscos e pendências;
19. confirmação de ausência de credenciais;
20. confirmação de ausência de commit, push e deploy.

Não avance para o `CURSOR-007`.

Aguarde a revisão do arquiteto.
