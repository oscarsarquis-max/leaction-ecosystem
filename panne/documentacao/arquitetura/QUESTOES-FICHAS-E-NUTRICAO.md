# Questões — fichas e nutrição

Classificação: **resolvida pelo DDL** | **inferência** | **decisão arquitetural** | **decisão do proprietário** | **decisão de especialista em panificação** | **decisão regulatória**.

O DDL não prova comportamento de cálculo nem regra sanitária. Texto armazenado no legado não é norma vigente.

| # | Questão | Classificação | Nota |
|---|---------|---------------|------|
| 1 | Um produto pode ser insumo, ficha e rótulo ao mesmo tempo? | Resolvida pelo DDL | Três flags `USO_*` `NOT NULL` independentes; sem exclusão mútua. |
| 2 | Há FK entre ficha e informação nutricional? | Resolvida pelo DDL | Não. Elo só inferido via `ID_PRODUTO`. |
| 3 | A linha da ficha tem unidade e ordem? | Resolvida pelo DDL | Não. |
| 4 | A linha nutricional tem PK? | Resolvida pelo DDL | Não. |
| 5 | Existem FKs, views ou triggers no núcleo? | Resolvida pelo DDL | Não (schema inteiro: 0 views, 0 triggers, 0 FKs). |
| 6 | A ficha tem número de versão ou aprovação? | Resolvida pelo DDL | Não. Há `DATA_ATUALIZACAO` e usuário. |
| 7 | Glúten/lactose são derivados? | Resolvida pelo DDL | Flags manuais `enum` na descrição. |
| 8 | kcal/%VD são numéricos oficiais? | Resolvida pelo DDL | Persistidos como `varchar` na tabela impressa. |
| 9 | PDF de ficha/rótulo está no banco? | Resolvida pelo DDL | Não. Só `DADOS_IMPRESSAO` no usuário. |
| 10 | `tbl_pop*` é documento da ficha? | Resolvida pelo DDL | Estrutura de POP/inspeção, não ficha. |
| 11 | `FC` é fator de correção de limpeza? | Inferência | Nome e `float(9,1)` na linha; fórmula não está no DDL. |
| 12 | `BASE_*` vs `QTDE_*` é origem × escalado? | Inferência | Padrão de colunas; sem prova. |
| 13 | `MC_MEDIDA` aponta `tbl_medida`? | Inferência | Tipos compatíveis; sem FK. |
| 14 | `OBSERVACAO` int é código de catálogo? | Inferência | Tipo opaco. |
| 15 | Totais do cabeçalho = soma das linhas? | Inferência | Colunas existem nos dois níveis; sem constraint. |
| 16 | Flags `USO_*` são exigidos pela aplicação para criar filhos? | Inferência | Banco não exige. |
| 17 | Fonte técnica única versionada | Decisão arquitetural | Adotada na proposta: `formulation_version`. |
| 18 | Não replicar produto polimórfico | Decisão arquitetural | Separar ingrediente / formulação / produto técnico / documento / rótulo. |
| 19 | Item aponta `ingredient_version`, não cabeça viva | Decisão arquitetural | Já alinhado ao catálogo existente. |
| 20 | Cálculo oficial imutável + evidência | Decisão arquitetural | `nutrition_calculation` + `calculation_evidence`. |
| 21 | Escala sem copiar linhas | Decisão arquitetural | `scale_calculation` em vez de `porcao*`. |
| 22 | `technical_product` obrigatório na v1? | Decisão arquitetural | Proposta o marca opcional. |
| 23 | Unique de insumo repetido na mesma versão | Decisão arquitetural + especialista | Mesma farinha em etapas distintas? |
| 24 | Uma `official` por versão e base | Decisão arquitetural | Unique parcial proposto. |
| 25 | Primeiro pão piloto | Decisão de especialista em panificação | Conceito ausente no DDL. Modelar como `trial`, não como versão publicada. Critérios de aceite do piloto (peso, miolo, perda) são do ofício. |
| 26 | Percentual do padeiro (baker’s %) | Decisão de especialista em panificação | Ausente no DDL. Se adotado, `bakers_percent_base` na versão. |
| 27 | Farinha como base | Decisão de especialista em panificação | DDL não marca farinha. Precisa regra de quais itens somam a 100%. |
| 28 | Pesos bruto e líquido | Resolvida pelo DDL (existência) + especialista (regra) | Colunas existem. Relação `líquido = bruto × FC` não está no banco. |
| 29 | Perdas | Resolvida pelo DDL (campo) + especialista | `PERDA_GANHO` e `FC` sem semântica fechada (perda vs ganho, quando aplicar). |
| 30 | Rendimento antes e depois do forno | Inferência + especialista | Há `PESO_COZIDO`, `FATOR_COCCAO`, `RENDIMENTO` e `RENDIMENTO_FINAL` em tabelas distintas. Qual entra no denominador nutricional é do ofício + norma. |
| 31 | Ingredientes compostos | Decisão arquitetural (capacidade) + especialista (uso) | Catálogo já tem `ingredient_composition`. Expandir no rótulo é regra de declaração. |
| 32 | Preparação usada como ingrediente | Inferência no legado + arquitetural na Panne | Legado permite via produto polimórfico. Panne: preparação no catálogo ou materialização de formulação publicada — **quando** materializar é decisão conjunta arquiteto/especialista. |
| 33 | Custo na ficha | Decisão do proprietário | Legado guarda custo na linha e no cabeçalho. Proposta tira custo do núcleo de conformidade. Incluir satélite comercial? |
| 34 | Porção | Inferência + regulatória + especialista | `PESO_PORCAO` na ficha e `PORCAO` na nutrição podem divergir. Qual é a porção legal vs a de produção. |
| 35 | Arredondamento | Decisão regulatória | DDL só mostra `varchar`. Regra (RDC vigente) + vigência em `data_source`. |
| 36 | Aprovação | Decisão do proprietário + arquitetural | Ausente no DDL. Quem aprova (técnico, RT, dono) e se bloqueia publicação. |
| 37 | Revisão técnica | Decisão do proprietário | Periodicidade, gatilho (troca de insumo) e se republica ficha e rótulo juntos. |
| 38 | Documento e rótulo | Decisão arquitetural + proprietário | Ficha derivada; rótulo = snapshot. Quem pode selar e onde o PDF vive (URI). |
| 39 | Cálculo nutricional | Decisão arquitetural + regulatória + especialista | Derivado da formulação. Soma linear? Perdas de cocção por nutriente? Água? Álcool? |
| 40 | Normas e vigência | Decisão regulatória | Qual RDC/IN; data de aplicação; coexistência de rótulos antigos. `data_source.valid_from/to` já existe no núcleo. |
| 41 | Medida caseira canônica | Decisão do proprietário + regulatória | Ligar a `measurement_unit` ou texto (“1 fatia”). Sem fator no legado. |
| 42 | Peso líquido de venda vs massa da fórmula | Decisão do proprietário + regulatória | No legado é campo do rótulo, separado dos totais da ficha. |
| 43 | IA preenche rascunho? | Decisão do proprietário | Proposta permite `evidence_kind = suggestion`; nunca oficial sozinha. |
| 44 | Isolamento multiempresa | Decisão arquitetural | Já: `organization_id` obrigatório. Legado tinha empresa anulável. |
| 45 | Produto comercial no mesmo bounded context? | Decisão do proprietário | Recomendação: não. Preço/canal fora. |

## Síntese do que o DDL fecha

Polimorfismo possível; duas composições sem ponte; sem versão/aprovação/PDF; nutrientes e alergênicos frágeis; pesos e rendimento **existem** mas sem fórmula.

## Síntese do que só o dono / ofício / norma fecham

Piloto, baker’s %, farinha-base, semântica de perda e forno, custo, porção legal, arredondamento, papéis de aprovação, vigência normativa.
