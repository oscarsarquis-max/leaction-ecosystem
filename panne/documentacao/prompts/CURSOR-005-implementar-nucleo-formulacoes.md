# CURSOR-005 — Implementar o núcleo de formulações

## Objetivo

Implemente o núcleo de produto técnico e formulações da Panne.

Crie a migração:

```text
0004_formulation_lab
```

A implementação deverá abranger:

- produto técnico;
- referências de receitas;
- formulações;
- versões;
- ingredientes da formulação;
- etapas de preparo;
- percentual do padeiro;
- escala determinística;
- memória de cálculo;
- testes de produção;
- medições;
- aprovação.

## Proteção do legado

Não acesse o MySQL legado neste ciclo.

Não use suas credenciais, não execute consultas e não modifique a base de origem.

Toda operação de banco deve ocorrer exclusivamente no PostgreSQL local da Panne.

Antes das migrações, confirme:

- mecanismo PostgreSQL;
- banco lógico `panne`;
- ambiente local ou teste;
- head inicial `0003_ingredient_catalog`.

Não exponha credenciais no retorno.

## Princípio central

`FormulationVersion` será a fonte técnica única.

Dela serão futuramente derivados:

- ficha técnica;
- escala;
- cálculo nutricional;
- documentos;
- rótulos;
- produção.

Não crie composições paralelas.

## Migração `0004_formulation_lab`

Crie as tabelas:

1. `technical_product`
2. `recipe_reference`
3. `formulation`
4. `formulation_recipe_reference`
5. `formulation_version`
6. `formulation_item`
7. `process_step`
8. `scale_calculation`
9. `scale_calculation_item`
10. `trial`
11. `trial_measurement`
12. `approval`

Use:

- UUID;
- `timestamptz` e UTC;
- `numeric` com precisão explícita;
- FKs;
- FKs compostas para isolamento organizacional;
- checks;
- unicidades;
- índices justificados;
- nomes físicos em `snake_case`;
- exclusão física bloqueada no fluxo normal.

## Produto técnico

### `technical_product`

Representa a identidade técnica de um produto em desenvolvimento.

Não é produto comercial.

Campos mínimos:

- `id`;
- `organization_id`;
- `code`;
- `display_name`;
- `description`;
- `status`;
- `created_at`;
- `updated_at`.

Estados iniciais:

- `development`;
- `approved`;
- `retired`.

Requisitos:

- código único dentro da organização;
- FK real para organização;
- nenhuma informação comercial;
- nenhum preço;
- nenhuma publicação em loja.

## Referências de receitas

### `recipe_reference`

Campos mínimos:

- `id`;
- `organization_id`;
- `title`;
- `source_type`;
- `source_url`, quando existir;
- `author`, quando conhecido;
- `license_or_usage_notes`;
- `accessed_at`;
- `notes`;
- `created_at`;
- `created_by_user_id`, quando disponível.

Requisitos:

- não armazenar cópia integral de conteúdo protegido;
- manter procedência;
- distinguir referência externa, interna e informada pelo usuário;
- não tratar referência como formulação oficial.

### `formulation_recipe_reference`

Tabela associativa entre formulação e referência.

Requisitos:

- mesma organização;
- vínculo único;
- papel da referência, como:
  - `inspiration`;
  - `source`;
  - `comparison`.

## Formulação

### `formulation`

Campos mínimos:

- `id`;
- `organization_id`;
- `technical_product_id`;
- `code`;
- `display_name`;
- `status`;
- `created_at`;
- `updated_at`.

Estados:

- `development`;
- `active`;
- `retired`.

Requisitos:

- pertence obrigatoriamente a um produto técnico;
- código único por organização;
- produto e formulação na mesma organização;
- pode possuir várias versões.

### `formulation_version`

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_id`;
- `version_number`;
- `status`;
- `yield_units`;
- `target_unit_weight_g`, quando aplicável;
- `expected_bake_loss_rate`, quando aplicável;
- `notes`;
- `created_at`;
- `created_by_user_id`, quando disponível;
- `published_at`, quando publicada.

Estados:

- `draft`;
- `published`;
- `retired`.

Requisitos:

- versão única por formulação;
- somente uma versão `published` por formulação;
- índice único parcial no PostgreSQL;
- versão publicada imutável;
- publicação depende de aprovação válida;
- nova alteração gera nova versão;
- não usar `current_version_id`;
- taxa de perda entre 0 e menor que 1;
- quantidades e pesos não negativos.

## Itens da formulação

### `formulation_item`

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `ingredient_version_id`;
- `sequence`;
- `net_quantity`;
- `measurement_unit_id`;
- `correction_factor`;
- `is_flour_basis`;
- `role`;
- `notes`;
- `created_at`.

Requisitos:

- formulação e ingrediente na mesma organização;
- apontar sempre para uma versão específica de ingrediente;
- sequência única dentro da versão;
- quantidade líquida positiva em `numeric(14,6)`;
- fator de correção positivo em `numeric(20,10)`;
- fator padrão igual a 1;
- quantidade bruta derivada:

```text
gross_quantity = net_quantity × correction_factor
```

Não armazene quantidade bruta como segunda fonte independente.

As quantidades canônicas do núcleo inicial devem usar unidades de massa.

Não aceite unidade incompatível com massa.

## Percentual do padeiro

Itens podem ser marcados como `is_flour_basis = true`.

A base de farinha é:

```text
total_flour_mass = soma das quantidades líquidas dos itens de farinha-base
```

Para cada item:

```text
bakers_percentage =
    net_mass / total_flour_mass × 100
```

Requisitos:

- usar `Decimal`;
- não usar ponto flutuante binário;
- percentual derivado, nunca fonte digitada independente;
- várias farinhas podem compor a base;
- formulação sem farinha-base é válida, mas não produz percentual do padeiro;
- se houver farinha-base, a soma deve ser maior que zero;
- registrar a política de precisão e arredondamento;
- testar formulações com uma e várias farinhas.

Não classifique automaticamente um ingrediente como farinha apenas pelo nome.

## Etapas de preparo

### `process_step`

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `sequence`;
- `title`;
- `instructions`;
- `duration_seconds`, quando aplicável;
- `temperature_celsius`, quando aplicável;
- `created_at`.

Requisitos:

- sequência única por versão;
- duração não negativa;
- temperatura com precisão explícita;
- versão publicada torna etapas imutáveis;
- não armazenar todo o preparo em um único campo sem estrutura.

## Motor determinístico de escala

Implemente o motor fora da camada HTTP e sem dependência de IA.

Modos iniciais:

### Modo A — massa total de massa

Entrada:

- formulação versionada;
- massa total desejada.

Cálculo:

```text
scale_factor =
    target_total_dough_mass / base_total_net_mass
```

### Modo B — unidades finais

Entradas:

- quantidade de unidades;
- peso final desejado por unidade;
- taxa prevista de perda no forno.

Cálculo:

```text
required_pre_bake_mass =
    units × final_unit_weight / (1 - bake_loss_rate)
```

```text
scale_factor =
    required_pre_bake_mass / base_total_net_mass
```

Para cada item:

```text
scaled_net_quantity =
    base_net_quantity × scale_factor
```

```text
scaled_gross_quantity =
    scaled_net_quantity × correction_factor
```

Requisitos:

- `Decimal`;
- divisão por zero impossível;
- taxa de perda entre 0 e menor que 1;
- quantidade de unidades inteira e positiva;
- pesos positivos;
- arredondamento explícito;
- padrão inicial: `ROUND_HALF_UP`;
- precisão de apresentação configurável, sem alterar o cálculo interno;
- nenhuma chamada a LLM.

## Memória de cálculo

### `scale_calculation`

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `calculation_mode`;
- entradas;
- massa-base;
- fator de escala;
- massa pré-forno necessária;
- algoritmo e versão;
- política de arredondamento;
- `created_at`;
- `created_by_user_id`, quando disponível.

### `scale_calculation_item`

Campos mínimos:

- `id`;
- `organization_id`;
- `scale_calculation_id`;
- `formulation_item_id`;
- `ingredient_version_id`;
- `sequence`;
- quantidade líquida calculada;
- quantidade bruta calculada;
- percentual do padeiro, quando aplicável;
- unidade;
- valores-base necessários à reconstrução.

Requisitos:

- resultado reconstruível;
- snapshot imutável;
- itens preservam as versões usadas;
- resultado não muda quando preços ou ingredientes posteriores forem alterados;
- nenhuma informação nutricional neste ciclo.

## Trials

### `trial`

Representa uma execução experimental.

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `code`;
- `status`;
- data planejada;
- data de execução;
- observações;
- `created_at`;
- `created_by_user_id`.

Estados:

- `planned`;
- `in_progress`;
- `completed`;
- `cancelled`.

### `trial_measurement`

Campos mínimos:

- `id`;
- `organization_id`;
- `trial_id`;
- `measurement_type`;
- `value`;
- `measurement_unit_id`, quando aplicável;
- `recorded_at`;
- `notes`.

Tipos iniciais documentados:

- massa real da massa;
- quantidade produzida;
- peso final unitário;
- perda real;
- tempo;
- temperatura.

Não transforme observações sensoriais em números artificiais.

## Aprovação

### `approval`

Deve ser append-only.

Campos mínimos:

- `id`;
- `organization_id`;
- `formulation_version_id`;
- `actor_user_id`;
- `decision`;
- `occurred_at`;
- `notes`;
- `correlation_id`, quando disponível.

Decisões:

- `submitted`;
- `approved`;
- `rejected`;
- `revoked`.

Requisitos:

- nenhuma atualização ou exclusão pela camada normal;
- aprovação refere-se a uma versão específica;
- uma versão só pode ser publicada após decisão `approved`;
- revogação não apaga a aprovação;
- política de papéis será aplicada futuramente com autenticação;
- não criar endpoint público de aprovação.

## Preparação usada como ingrediente

Não implemente automaticamente a publicação de formulação como ingrediente neste ciclo.

Documente a fronteira futura:

- formulação aprovada;
- publicação técnica explícita;
- criação de `IngredientVersion` de tipo `preparation`;
- rastreabilidade até a `FormulationVersion` de origem;
- nenhuma referência polimórfica em `formulation_item`.

## Custos

Não implemente custo neste ciclo.

Documente que:

- preços vêm de `supplier_item_price`;
- custo será cálculo satélite;
- custo produzirá snapshot próprio;
- preço comercial não pertence à formulação;
- alterações de preço não mudam versões aprovadas.

## Imutabilidade e integridade

Garanta na camada de domínio e, quando apropriado, no PostgreSQL:

- versões publicadas imutáveis;
- itens e etapas de versão publicada imutáveis;
- cálculos persistidos imutáveis;
- approvals append-only;
- trials concluídos preservados;
- isolamento entre organizações;
- ausência de relações cruzadas entre organizações.

## Testes obrigatórios

Use PostgreSQL real e Python 3.12.

Cubra pelo menos:

### Migração

- upgrade de `0003` para `0004`;
- downgrade para `0003`;
- novo upgrade;
- criação em banco vazio até head.

### Produto e formulação

- código único por organização;
- mesmo código permitido em organizações diferentes;
- produto e formulação de organizações diferentes rejeitados;
- versão única;
- apenas uma versão publicada;
- publicação sem aprovação rejeitada;
- versão publicada imutável.

### Itens

- ingrediente de outra organização rejeitado;
- versão de ingrediente inexistente rejeitada;
- unidade não mássica rejeitada;
- sequência duplicada rejeitada;
- quantidade inválida rejeitada;
- fator inválido rejeitado;
- bruto derivado corretamente.

### Percentual do padeiro

- uma farinha;
- múltiplas farinhas;
- soma da base;
- formulação sem farinha;
- quantidade zero inválida;
- precisão decimal.

### Escala

- por massa total;
- por unidades finais;
- perda zero;
- perda válida;
- perda igual ou superior a 1 rejeitada;
- resultado reproduzível;
- memória consistente;
- arredondamento na metade;
- nenhuma diferença decorrente de `float`.

### Preparo, trials e aprovação

- sequência de preparo;
- valores inválidos;
- trial em outra organização rejeitado;
- medição inválida;
- approval append-only;
- revogação preserva histórico.

## Endpoints

Não crie CRUD.

Mantenha somente os endpoints técnicos já existentes:

- `/health`;
- `/ready`.

Não exponha formulações por HTTP neste ciclo.

## Documentação

Crie ou atualize:

- modelo de domínio;
- diagrama Mermaid;
- migração `0004`;
- invariantes;
- percentual do padeiro;
- fórmula de escala;
- precisão e arredondamento;
- memória de cálculo;
- trials;
- aprovação;
- fronteira preparação-como-ingrediente;
- fronteira de custos;
- riscos residuais.

Registre este prompt integralmente em `documentacao/prompts/`.

Registre o retorno em `documentacao/retornos/`.

## Restrições

- Não acessar o MySQL legado.
- Não criar nutrição ou rótulo.
- Não implementar conformidade.
- Não integrar IA.
- Não criar autenticação.
- Não criar CRUD ou frontend funcional.
- Não criar produto comercial.
- Não criar custo ou preço comercial.
- Não inserir dados reais.
- Não alterar outras aplicações.
- Não fazer commit, push ou deploy.

## Critérios de aceite

- migração `0004_formulation_lab` reversível;
- produto técnico separado de produto comercial;
- formulações e versões íntegras;
- fonte única de composição;
- itens ligados a versões de ingredientes;
- percentual do padeiro determinístico;
- escala por massa e unidades finais;
- memória de cálculo reconstruível;
- etapas ordenadas;
- trials e medições preservados;
- aprovação append-only;
- publicação dependente de aprovação;
- isolamento multiempresa;
- testes em PostgreSQL e Python 3.12;
- nenhuma credencial;
- nenhuma expansão indevida.

## Retorno obrigatório

Entregue:

1. confirmação de que o MySQL não foi acessado;
2. validação do PostgreSQL alvo;
3. arquivos criados e alterados;
4. tabelas, colunas e restrições;
5. regras de versionamento;
6. regra de quantidade líquida e fator de correção;
7. cálculo do percentual do padeiro;
8. modos e fórmulas de escala;
9. política de precisão e arredondamento;
10. memória de cálculo;
11. trials e medições;
12. aprovação e revogação;
13. upgrade, downgrade e reaplicação;
14. testes executados e resultados;
15. execução em Python 3.12;
16. `git diff --stat` e `git status --short`;
17. alterações preexistentes preservadas;
18. riscos e pendências;
19. confirmação de ausência de credenciais;
20. confirmação de ausência de commit, push e deploy.

Não avance para o `CURSOR-006`.

Aguarde a revisão do arquiteto.
