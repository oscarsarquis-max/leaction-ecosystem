# CURSOR-002 — Analisar o DDL legado de ingredientes

## Objetivo

Analise, exclusivamente em modo de leitura, o DDL do banco MySQL legado relacionado a ingredientes.

Use esse conhecimento para produzir o modelo conceitual e relacional proposto para o PostgreSQL da Panne.

Não copie tabelas mecanicamente e não crie ainda migrações ou tabelas novas na Panne.

## Princípio arquitetural

O desenho do banco legado é um ativo criado pelos consultores.

Devemos aproveitar:

- entidades;
- relações;
- cardinalidades;
- chaves;
- restrições;
- tabelas associativas;
- precisão dos campos;
- estados;
- versionamento;
- rastreabilidade;
- decisões de domínio implícitas.

O resultado deverá ser um modelo novo para a Panne, adequado a PostgreSQL, Python e aos requisitos atuais.

## Etapa inicial — Python 3.12

A fundação declara Python 3.12 como versão mínima, mas ainda não foi executada nesse runtime.

Antes da análise do banco:

1. procure um mecanismo local e reproduzível para validar o backend em Python 3.12;
2. não instale globalmente o Python 3.12;
3. não altere runtimes de outras aplicações;
4. pode utilizar container isolado, se compatível com o workspace;
5. execute pytest, Ruff e inicialização do backend;
6. documente o resultado.

Essa validação não deve impedir a análise documental do DDL caso o runtime continue indisponível. Registre objetivamente a limitação.

## Segurança do acesso ao legado

As credenciais devem ser fornecidas ao processo por configuração local e não versionada.

Não:

- escreva credenciais no prompt;
- grave credenciais em arquivos;
- mostre credenciais no terminal ou retorno;
- inclua host, usuário ou senha na documentação;
- altere permissões do usuário do banco;
- crie cópia integral da base;
- consulte registros de negócio.

Antes da inspeção, confirme que serão executadas apenas operações de metadados.

Quando suportado pelo cliente e pelo servidor, configure a sessão ou transação explicitamente como somente leitura.

## Operações permitidas

Somente consultas estruturais equivalentes a:

- catálogo `information_schema`;
- listagem de tabelas;
- listagem de colunas;
- tipos, tamanhos, precisão e nulabilidade;
- valores padrão;
- chaves primárias;
- chaves estrangeiras;
- restrições de unicidade;
- índices;
- tabelas associativas;
- `SHOW CREATE TABLE`;
- metadados de views relacionadas;
- metadados de triggers relacionadas, sem executá-las.

## Operações proibidas

Não execute:

- `INSERT`;
- `UPDATE`;
- `DELETE`;
- `CREATE`;
- `ALTER`;
- `DROP`;
- `TRUNCATE`;
- `REPLACE`;
- `CALL`;
- procedimentos ou funções armazenadas;
- comandos administrativos;
- mudanças de sessão que permitam escrita;
- consultas `SELECT` às linhas das tabelas de negócio;
- exportação de dados;
- dump contendo dados;
- bloqueio explícito de tabelas.

Se qualquer ferramenta tentar executar escrita, bloqueio ou leitura de registros, interrompa a operação.

## Descoberta das estruturas relevantes

Localize tabelas, colunas, índices e relações associados direta ou indiretamente a termos e conceitos como:

- ingrediente;
- ingredientes de ficha;
- matéria-prima;
- insumo;
- produto;
- ficha técnica;
- composição;
- informação nutricional;
- nutriente;
- porção;
- medida;
- unidade;
- conversão;
- rendimento;
- perda;
- fator de correção;
- alergênico;
- glúten;
- lactose;
- fornecedor;
- marca;
- fabricante;
- custo;
- empresa;
- usuário;
- histórico;
- versão.

Não presuma que os nomes utilizam exatamente essas palavras.

Utilize chaves, nomes de colunas e tabelas associativas para encontrar dependências adicionais.

## Análise obrigatória do legado

Para cada estrutura relevante, documente:

1. nome técnico no legado;
2. finalidade aparente;
3. colunas relevantes;
4. chave primária;
5. chaves estrangeiras declaradas;
6. relações inferidas quando não houver chave estrangeira;
7. índices e unicidades;
8. nulabilidade;
9. valores padrão;
10. tipos, tamanhos e precisão;
11. campos de empresa ou usuário;
12. controle de situação, bloqueio ou exclusão lógica;
13. campos de criação e atualização;
14. indícios de versionamento;
15. dependência com ficha técnica;
16. dependência com informação nutricional;
17. riscos e ambiguidades.

Marque claramente como **inferência** qualquer relação que não esteja declarada no DDL.

Não trate uma inferência como regra confirmada.

## Questões fundamentais

A análise deve responder, quando o DDL permitir:

- O ingrediente é global, pertencente à empresa ou híbrido?
- Ingrediente e matéria-prima representam o mesmo conceito?
- Existem ingredientes compostos?
- Uma preparação pode ser usada como ingrediente de outra ficha?
- Como unidades e medidas são representadas?
- Existem fatores de conversão?
- Como peso bruto e peso líquido são tratados?
- Como perdas e rendimento são representados?
- Onde ficam os nutrientes?
- Os nutrientes são armazenados por 100 g, por porção ou em outra base?
- Existe fonte ou versão do dado nutricional?
- Como alergênicos são relacionados aos ingredientes?
- Glúten e lactose são campos manuais ou derivados?
- Como ingredientes são relacionados à ficha técnica?
- Existe ordem de declaração dos ingredientes?
- Há tratamento para ingredientes compostos na rotulagem?
- Há custo e histórico de preço?
- Como empresa e usuário participam do cadastro?
- Existem versões ou apenas sobrescrita do estado atual?
- Quais decisões parecem estar implementadas somente fora do banco?

## Matriz de decisão

Produza uma matriz com quatro classificações:

### Preservar

Conceitos e relações tecnicamente válidos que devem permanecer no novo domínio.

### Repensar

Conhecimento valioso cuja modelagem atual limita versionamento, rastreabilidade, conformidade ou operação multiempresa.

### Descartar

Estruturas técnicas circunstanciais, duplicações, campos obsoletos ou decisões incompatíveis com o novo produto.

### Criar

Conceitos ausentes necessários à Panne, incluindo:

- origem dos dados;
- versionamento;
- vigência;
- precisão;
- ingredientes compostos;
- rastreabilidade;
- evidências;
- isolamento multiempresa;
- preparação para grounding e conformidade.

## Modelo conceitual da Panne

Com base na análise, proponha um modelo conceitual novo.

Considere, sem assumir antecipadamente que todos serão necessários:

- `Ingredient`;
- `IngredientVersion`;
- `IngredientComposition`;
- `IngredientNutrient`;
- `NutrientDefinition`;
- `MeasurementUnit`;
- `UnitConversion`;
- `Allergen`;
- `IngredientAllergen`;
- `DataSource`;
- `SupplierItem`;
- `OrganizationIngredient`;
- `FormulaIngredient`, apenas como fronteira futura.

Explique:

- responsabilidade de cada entidade;
- agregados;
- identidades;
- entidades globais e organizacionais;
- objetos versionados;
- invariantes;
- relações;
- decisões pendentes.

Não implemente essas entidades neste prompt.

## Proposta relacional PostgreSQL

Produza uma proposta de tabelas PostgreSQL sem gerar migração.

Para cada tabela proposta, documente:

- nome;
- finalidade;
- colunas;
- tipos PostgreSQL;
- chave primária;
- chaves estrangeiras;
- restrições;
- unicidades;
- índices;
- campos de auditoria;
- estratégia de versionamento;
- escopo global ou organizacional.

Use:

- nomes em `snake_case`;
- UUID para identificadores;
- `timestamptz` e UTC;
- `numeric` com precisão explícita para grandezas;
- restrições no banco;
- JSONB apenas quando a estrutura realmente não for relacional ou estável.

Não reproduza tipos e nomes do MySQL sem justificativa.

## Documentação obrigatória

Crie dentro da área documental da Panne:

1. `legado/DDL-INGREDIENTES-INVENTARIO.md`
2. `legado/DDL-INGREDIENTES-RELACIONAMENTOS.md`
3. `arquitetura/MATRIZ-LEGADO-INGREDIENTES.md`
4. `arquitetura/MODELO-CONCEITUAL-INGREDIENTES.md`
5. `arquitetura/PROPOSTA-POSTGRESQL-INGREDIENTES.md`
6. `arquitetura/QUESTOES-INGREDIENTES.md`

Inclua diagramas Mermaid simples para:

- relações observadas no legado;
- modelo conceitual proposto para a Panne.

Não registre credenciais, dados pessoais ou registros de negócio.

Não grave um dump completo do legado no repositório.

Registre este prompt integralmente em `documentacao/prompts/`.

Registre o retorno em `documentacao/retornos/`.

## Restrições da aplicação

- Não criar tabelas na Panne.
- Não criar migrações Alembic.
- Não alterar modelos SQLAlchemy.
- Não implementar APIs.
- Não alterar o frontend.
- Não implementar ingredientes.
- Não implementar fichas ou formulações.
- Não integrar IA.
- Não criar infraestrutura AWS.
- Não acessar dados do legado.
- Não modificar outras aplicações.
- Não fazer commit, push ou deploy.

## Critérios de aceite

- somente metadados e DDL foram consultados;
- nenhuma linha de negócio foi recuperada;
- nenhuma escrita ocorreu no banco legado;
- conjunto estrutural de ingredientes foi inventariado;
- relacionamentos explícitos e inferidos foram separados;
- decisões úteis do legado foram identificadas;
- matriz preservar, repensar, descartar e criar foi produzida;
- modelo conceitual novo foi proposto;
- proposta PostgreSQL foi documentada sem implementação;
- dúvidas e riscos foram explicitados;
- nenhuma credencial foi registrada;
- nenhuma outra aplicação foi alterada.

## Retorno obrigatório

Entregue:

1. confirmação do modo somente leitura;
2. comandos ou categorias de consultas estruturais executadas, sem credenciais;
3. lista das tabelas legadas analisadas;
4. resumo dos principais relacionamentos;
5. decisões valiosas identificadas;
6. principais fragilidades do desenho atual;
7. matriz resumida de preservação;
8. modelo conceitual proposto;
9. lista de tabelas PostgreSQL propostas;
10. documentos criados;
11. resultado da validação em Python 3.12;
12. `git diff --stat` e `git status --short`;
13. confirmação de que nenhuma linha de negócio foi consultada;
14. confirmação de que nenhuma escrita ocorreu no legado;
15. confirmação de que nenhuma tabela ou migração foi criada na Panne;
16. riscos, dúvidas e pendências.

Não avance para o `CURSOR-003`.

Não faça commit, push ou deploy.

Aguarde a revisão do arquiteto.
