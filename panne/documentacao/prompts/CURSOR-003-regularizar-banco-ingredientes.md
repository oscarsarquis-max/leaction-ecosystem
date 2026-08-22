# CURSOR-003 — Regularizar o banco e consolidar o núcleo de ingredientes

## Objetivo

Audite a migração `0002_ingredient_catalog`, criada antecipadamente no ciclo anterior, e consolide uma sequência limpa de migrações PostgreSQL para:

1. fundação multiempresa;
2. catálogo técnico de ingredientes;
3. versionamento;
4. composição;
5. nutrientes;
6. alergênicos;
7. fornecedores e histórico de preços;
8. auditoria.

Não implemente APIs funcionais, autenticação, fichas técnicas ou interface.

## Proteção absoluta do banco de origem

O banco MySQL legado é somente fonte histórica de conhecimento.

Ele não pode ser modificado em nenhuma circunstância.

### Proibido na origem

Não execute no MySQL legado:

- `INSERT`;
- `UPDATE`;
- `DELETE`;
- `REPLACE`;
- `CREATE`;
- `ALTER`;
- `DROP`;
- `TRUNCATE`;
- migrações;
- seeds;
- testes que escrevam;
- criação de tabelas temporárias;
- bloqueios explícitos;
- procedimentos;
- funções;
- triggers;
- mudanças de permissões;
- importação ou exportação de dados;
- qualquer comando administrativo ou mutável.

Não use o banco de origem como banco de testes.

Não direcione Alembic, SQLAlchemy, pytest ou scripts da Panne para o MySQL.

Não grave credenciais da origem em arquivos, logs, documentação ou retorno.

## Banco autorizado para alterações

Toda operação mutável deste prompt deve ocorrer exclusivamente no PostgreSQL local da aplicação Panne.

Antes de executar migrações ou testes destrutivos, confirme:

- mecanismo: PostgreSQL;
- banco: `panne`;
- ambiente: local ou teste;
- ausência de dados de produção;
- ausência de consumidores externos;
- ausência de conexão com o host MySQL legado.

Mostre no retorno apenas mecanismo, nome lógico e ambiente. Não revele host, usuário ou senha.

Se qualquer validação indicar MySQL, produção, banco compartilhado incorreto ou ambiente desconhecido, interrompa imediatamente sem executar alterações.

## Parte 1 — Validação da fundação

Execute novamente a validação com Python 3.12 em ambiente isolado e reproduzível:

- instalação das dependências;
- pytest;
- Ruff check;
- Ruff format check;
- inicialização da aplicação;
- `GET /health`.

Não instale Python globalmente e não altere outras aplicações.

## Parte 2 — Auditoria da migração antecipada

Audite integralmente:

```text
0002_ingredient_catalog
```

Verifique:

- tabelas;
- colunas;
- tipos;
- precisão;
- nulabilidade;
- defaults;
- chaves primárias;
- chaves estrangeiras;
- ações de atualização e exclusão;
- restrições;
- unicidades;
- índices;
- estados;
- versionamento;
- isolamento organizacional;
- composição;
- nutrientes;
- alergênicos;
- fornecedores;
- preços;
- reversibilidade;
- testes existentes.

Compare a implementação com:

- requisitos da Panne;
- análise do DDL legado;
- matriz preservar/repensar/descartar/criar;
- modelo conceitual aprovado;
- decisões deste prompt.

Documente cada divergência antes de corrigi-la.

## Parte 3 — Condição para reorganizar migrações

A migração antecipada ainda não foi aprovada nem versionada por commit.

Antes de reescrevê-la, renumerá-la ou revertê-la, confirme que:

- está somente no ambiente local;
- não existe em ambiente compartilhado;
- não possui dados;
- não foi consumida por outro desenvolvedor;
- não houve commit, push ou deploy;
- a reversão afeta exclusivamente o PostgreSQL `panne`.

Se todas as condições forem verdadeiras, organize a sequência como:

```text
0001_foundation
0002_organization_foundation
0003_ingredient_catalog
```

Preserve `0001_foundation`.

É permitido reverter a migração antecipada somente no PostgreSQL local vazio da Panne para reorganizar a sequência.

Se alguma condição não for comprovada, não reescreva o histórico. Crie migrações adicionais de correção e explique a estratégia.

## Parte 4 — Fundação multiempresa

Crie a migração:

```text
0002_organization_foundation
```

### `organization`

Campos mínimos:

- `id` UUID;
- `slug`;
- `legal_name`;
- `display_name`;
- `status`;
- `created_at`;
- `updated_at`.

Requisitos:

- `slug` único;
- status validado;
- datas em `timestamptz`, UTC;
- nenhuma exclusão física no fluxo normal.

### `establishment`

Campos mínimos:

- `id`;
- `organization_id`;
- `code`;
- `display_name`;
- `status`;
- `created_at`;
- `updated_at`.

Requisitos:

- FK obrigatória para organização;
- código único dentro da organização;
- não exigir CNPJ ou endereço nesta etapa.

### `app_user`

Representa identidade global, ainda sem autenticação.

Campos mínimos:

- `id`;
- `email`;
- `display_name`;
- `status`;
- `created_at`;
- `updated_at`.

Requisitos:

- e-mail único sem diferenciação entre maiúsculas e minúsculas;
- nenhuma senha;
- nenhum token;
- nenhum provedor de login.

Use `app_user`, ou outro nome não reservado aprovado e documentado, em vez de `user`.

### `organization_membership`

Campos mínimos:

- `id`;
- `organization_id`;
- `user_id`;
- `role`;
- `status`;
- `created_at`;
- `updated_at`.

Requisitos:

- vínculo único entre usuário e organização;
- FKs obrigatórias;
- papéis iniciais:
  - `owner`;
  - `administrator`;
  - `technical_responsible`;
  - `production`;
  - `commercial`;
  - `viewer`.

Não implemente autenticação ou autorização completa.

### `audit_event`

Campos mínimos:

- `id`;
- `organization_id`, quando aplicável;
- `actor_user_id`, quando conhecido;
- `event_type`;
- `aggregate_type`;
- `aggregate_id`;
- `occurred_at`;
- `correlation_id`, quando disponível;
- `payload` JSONB.

Requisitos:

- append-only;
- sem `updated_at`;
- sem atualização ou exclusão pela camada normal;
- eventos de sistema podem não possuir ator;
- não registrar credenciais ou dados pessoais desnecessários.

## Parte 5 — Catálogo de ingredientes

Crie:

```text
0003_ingredient_catalog
```

A migração deve conter o modelo auditado e regularizado.

### Catálogos globais

- `measurement_unit`;
- `unit_conversion`;
- `nutrient_definition`;
- `allergen`;
- `data_source`.

Requisitos:

- identificadores UUID;
- códigos únicos;
- status explícito quando aplicável;
- nenhuma informação específica de organização;
- unidades com dimensão explícita;
- conversões somente entre unidades compatíveis;
- fator de conversão `numeric(20,10)` e positivo;
- nutrientes ligados à unidade de declaração;
- fontes com tipo, referência, versão e vigência quando disponíveis.

Não permita conversões universais entre massa e volume. Conversões dependentes de densidade exigirão tratamento específico futuro.

### `ingredient`

O ingrediente pertence exclusivamente a uma organização.

Campos mínimos:

- `id`;
- `organization_id`;
- `code`;
- `display_name`;
- `ingredient_type`;
- `status`;
- `created_at`;
- `updated_at`.

Requisitos:

- FK real para `organization`;
- código único dentro da organização;
- tipo validado:
  - `simple`;
  - `composite`;
  - `preparation`;
- nenhum `organization_ingredient`;
- nenhuma exclusão física no fluxo normal.

### `ingredient_version`

Campos mínimos:

- `id`;
- `ingredient_id`;
- `version_number`;
- `status`;
- `data_source_id`, quando disponível;
- base nutricional;
- datas de vigência;
- `created_at`;
- `created_by_user_id`, quando disponível;
- observações técnicas opcionais.

Requisitos:

- versão única por ingrediente;
- estados validados:
  - `draft`;
  - `published`;
  - `retired`;
- no máximo uma versão `published` por ingrediente;
- essa regra deve ser garantida no PostgreSQL por índice único parcial ou mecanismo equivalente;
- versão publicada não pode ser alterada pela camada normal;
- alterações posteriores criam nova versão;
- não usar `current_version_id`.

### Base nutricional

A base canônica será `per_100g`, mas não deve ficar implícita.

Registre estruturalmente:

- tipo da base;
- quantidade-base;
- unidade-base.

Requisitos:

- quantidade-base igual a 100;
- unidade-base de massa compatível com grama;
- nutrientes em `numeric(14,6)`;
- valores não negativos;
- rótulos por porção serão derivados futuramente;
- nutrição do ingrediente não é a tabela nutricional do produto final.

### `ingredient_composition`

Representa ingredientes compostos e preparações usadas como insumo.

Campos mínimos:

- `id`;
- `organization_id`;
- `parent_ingredient_version_id`;
- `component_ingredient_version_id`;
- `component_type`;
- `quantity`;
- `measurement_unit_id`;
- `sequence`;
- `created_at`.

Tipos:

- `constituent`;
- `preparation`.

Requisitos:

- componente e pai devem pertencer à mesma organização;
- pai não pode referenciar a si mesmo;
- sequência única dentro da versão;
- quantidade positiva em `numeric(14,6)`;
- unidade obrigatória;
- impedir ciclos por validação de domínio com testes;
- referenciar versões específicas, nunca apenas o ingrediente abstrato;
- preservar a ordem necessária à composição e futura rotulagem.

### `ingredient_nutrient`

Requisitos:

- FK para versão do ingrediente;
- FK para definição do nutriente;
- valor `numeric(14,6)`;
- valor não negativo;
- unicidade entre versão e nutriente;
- base herdada explicitamente da versão.

### `ingredient_allergen`

Requisitos:

- FK para versão do ingrediente;
- FK para alergênico;
- classificação validada, como:
  - `contains`;
  - `may_contain`;
  - `not_declared`;
- unicidade entre versão e alergênico;
- fonte ou evidência quando disponível;
- não derivar automaticamente glúten ou lactose sem regra normativa futura.

## Parte 6 — Fornecedores

A criação antecipada de `supplier_item` e `supplier_item_price` exige um agregado de fornecedor.

Crie `supplier` como entidade pertencente à organização, contendo apenas:

- `id`;
- `organization_id`;
- `code`;
- `display_name`;
- `status`;
- `created_at`;
- `updated_at`.

Não implemente endereço, CNPJ, marketplace ou compras.

### `supplier_item`

Deve relacionar:

- organização;
- fornecedor;
- ingrediente;
- código do item no fornecedor;
- descrição;
- quantidade da embalagem;
- unidade;
- status.

Requisitos:

- fornecedor e ingrediente devem pertencer à mesma organização;
- embalagem positiva;
- unicidade coerente por fornecedor;
- nenhuma dependência de Amazon ou marketplace.

### `supplier_item_price`

Histórico append-only:

- `id`;
- `supplier_item_id`;
- preço `numeric(14,4)`;
- moeda ISO;
- data de observação ou vigência;
- fonte;
- `created_at`.

Requisitos:

- preço não negativo;
- nenhuma atualização destrutiva de histórico;
- nenhuma informação comercial inserida como dado permanente neste prompt.

## Parte 7 — Conceitos preservados para etapas futuras

Documente, sem implementar ainda, onde entrarão posteriormente:

- peso bruto;
- peso líquido;
- fator de correção;
- perdas;
- rendimento;
- cocção;
- quantidades de fórmula;
- ordem de ingredientes no produto final;
- ficha técnica;
- tabela nutricional do produto final.

Esses conceitos não devem ser perdidos nem colocados arbitrariamente em `ingredient_version`.

## Integridade multiempresa

Toda tabela organizacional deve possuir `organization_id` explícito quando isso for necessário para integridade.

Implemente FKs e restrições que impeçam relações entre organizações diferentes.

Quando uma FK simples não garantir o isolamento, use:

- chaves únicas compostas;
- FKs compostas;
- validação determinística de domínio;
- testes negativos.

Não implemente RLS ainda. Documente o risco residual e a futura avaliação junto com autenticação.

## Testes obrigatórios

Amplie significativamente os quatro testes existentes.

Cubra pelo menos:

### Migrações

- upgrade completo em PostgreSQL vazio;
- downgrade até `0001`;
- novo upgrade até head;
- esquema final esperado;
- nenhuma alteração fora do banco `panne`.

### Organizações

- slug único;
- estabelecimento restrito à organização;
- vínculo único de usuário;
- e-mail sem diferenciação por caixa;
- evento de auditoria append-only.

### Ingredientes

- código único por organização;
- mesmo código permitido em organizações diferentes;
- versão única;
- apenas uma versão publicada;
- tentativa de alteração de versão publicada bloqueada pela camada normal;
- base nutricional válida;
- nutriente único por versão;
- valores negativos rejeitados;
- composição na mesma organização;
- autorreferência rejeitada;
- ciclo indireto rejeitado;
- sequência única;
- componente em outra organização rejeitado;
- alergênico único por versão.

### Fornecedores

- fornecedor e ingrediente na mesma organização;
- item cruzando organizações rejeitado;
- embalagem inválida rejeitada;
- preço negativo rejeitado;
- histórico de preços preservado.

Use PostgreSQL real e isolado. Não use MySQL e não consulte o legado durante os testes.

## Endpoints técnicos

Mantenha `/health` independente do banco.

Mantenha ou crie `/ready` para validar somente a disponibilidade do PostgreSQL da Panne.

Não exponha credenciais, endereço ou detalhes internos.

Não crie endpoints CRUD.

## Documentação obrigatória

Atualize:

- modelo de dados;
- diagrama Mermaid;
- decisões de versionamento;
- base nutricional;
- isolamento multiempresa;
- política append-only;
- fronteiras futuras;
- comandos de migração;
- testes;
- riscos residuais.

Registre este prompt integralmente em `documentacao/prompts/`.

Registre o retorno em `documentacao/retornos/`.

## Restrições

- Não modificar o MySQL legado.
- Não consultar linhas do legado.
- Não copiar DDL mecanicamente.
- Não implementar autenticação.
- Não criar CRUD.
- Não alterar o frontend.
- Não implementar fichas ou formulações.
- Não implementar conformidade normativa.
- Não integrar IA, Claude ou Bedrock.
- Não criar infraestrutura AWS.
- Não alterar outras aplicações.
- Não inserir dados reais.
- Não fazer commit, push ou deploy.

## Critérios de aceite

- origem MySQL completamente preservada;
- operações mutáveis executadas somente no PostgreSQL local `panne`;
- sequência de migrações organizada e justificada;
- fundação multiempresa implementada;
- ingrediente pertencente à organização;
- catálogos globais implementados;
- versionamento imutável e versão publicada única;
- base `per_100g` explícita;
- composição com integridade e prevenção de ciclos;
- nutrientes e alergênicos normalizados;
- fornecedor devidamente modelado;
- histórico de preços preservado;
- testes suficientes para os invariantes;
- upgrade, downgrade e reaplicação comprovados;
- nenhuma credencial versionada;
- nenhuma funcionalidade futura antecipada.

## Retorno obrigatório

Entregue:

1. confirmação explícita de que o MySQL legado não foi modificado;
2. validação do PostgreSQL alvo antes das operações;
3. resultado da auditoria da antiga `0002`;
4. estratégia adotada para reorganizar ou corrigir migrações;
5. arquivos criados e alterados;
6. tabelas, colunas, FKs, checks, unicidades e índices finais;
7. regras de isolamento multiempresa;
8. regras de versionamento;
9. tratamento da base nutricional;
10. prevenção de ciclos;
11. tratamento de fornecedores e preços;
12. upgrade, downgrade e reaplicação;
13. testes executados e resultados;
14. resultado em Python 3.12;
15. comportamento de `/health` e `/ready`;
16. `git diff --stat` e `git status --short`;
17. alterações preexistentes preservadas;
18. riscos e pendências;
19. confirmação de ausência de credenciais;
20. confirmação de ausência de commit, push e deploy.

Não avance para o `CURSOR-004`.

Aguarde a revisão do arquiteto.
