# CURSOR-004 — Analisar fichas técnicas, produtos e informação nutricional

## Objetivo

Analise exclusivamente por metadados e DDL o núcleo do sistema legado relacionado a:

- produtos;
- fichas técnicas;
- ingredientes das fichas;
- etapas de preparo;
- porções;
- rendimento;
- informação nutricional;
- ingredientes declarados;
- alergênicos;
- observações;
- documentos técnicos.

Confronte esse desenho com o catálogo de ingredientes já criado na Panne e proponha o novo modelo conceitual e relacional.

Não implemente tabelas ou funcionalidades neste prompt.

## Proteção absoluta do MySQL legado

O banco MySQL legado é estritamente somente leitura.

Não execute:

- escrita;
- alteração de estrutura;
- migração;
- seed;
- teste mutável;
- criação de tabela temporária;
- bloqueio;
- rotina armazenada;
- comando administrativo;
- consulta a linhas de negócio;
- exportação de dados.

Use somente:

- `information_schema`;
- colunas;
- constraints;
- índices;
- chaves;
- views;
- triggers;
- `SHOW CREATE TABLE`.

Configure a sessão e a transação como somente leitura.

Não grave credenciais em arquivos, logs, documentos ou retorno.

## Proibição de implementação antecipada

Neste ciclo, não:

- crie migrações Alembic;
- altere modelos SQLAlchemy;
- crie tabelas PostgreSQL;
- altere APIs;
- altere frontend;
- crie seeds;
- implemente cálculos;
- faça commit, push ou deploy.

O resultado deste prompt é exclusivamente arquitetural e documental.

## Estruturas a investigar

Analise todas as tabelas e dependências relacionadas, incluindo as identificadas anteriormente:

- `tbl_produto`;
- `tbl_produto_preco`;
- `tbl_ficha_tecnica`;
- tabelas de ingredientes da ficha;
- tabelas de modo de preparo;
- tabelas de porção;
- `tbl_info_nutricional`;
- tabelas de descrição nutricional;
- tabelas de ingredientes declarados;
- tabelas nutricionais;
- observações;
- medidas;
- empresas;
- usuários;
- permissões;
- tabelas de impressão ou documentos quando representadas no banco.

Descubra estruturas adicionais por nomes, colunas `ID_*`, índices e tabelas associativas.

Não presuma que as relações inferidas sejam regras confirmadas.

## Análise obrigatória

Para cada tabela relevante, documente:

1. finalidade aparente;
2. chave primária;
3. colunas;
4. tipos e precisão;
5. nulabilidade;
6. defaults;
7. índices;
8. unicidades;
9. FKs declaradas;
10. relações inferidas;
11. escopo por empresa;
12. vínculo com usuário;
13. estados, bloqueios e exclusão lógica;
14. criação e atualização;
15. indícios de versionamento;
16. campos de peso;
17. campos de quantidade;
18. unidades;
19. rendimento;
20. perdas;
21. cocção;
22. porções;
23. nutrientes;
24. ingredientes declarados;
25. alergênicos;
26. glúten e lactose;
27. texto livre;
28. observações;
29. geração de documentos.

## Produto polimórfico

A análise anterior identificou flags `USO_*` em `tbl_produto`.

Determine pelo DDL:

- quais papéis um produto pode assumir;
- se um mesmo produto atua como insumo, item de ficha e item de rotulagem;
- quais tabelas dependem desses flags;
- quais conflitos podem surgir;
- quais conceitos estão misturados.

Proponha a separação adequada no novo domínio entre:

- ingrediente;
- formulação;
- produto técnico;
- produto comercial;
- documento técnico;
- rótulo.

Não replique o modelo polimórfico sem justificativa.

## Ficha técnica

Investigue:

- identidade da ficha;
- vínculo com empresa;
- vínculo com produto;
- composição;
- quantidade bruta;
- quantidade líquida;
- fator de correção;
- unidade;
- ordem dos ingredientes;
- peso total;
- rendimento;
- peso unitário;
- perdas;
- cocção;
- porções;
- custo;
- etapas e modo de preparo;
- responsável;
- data;
- aprovação;
- situação;
- histórico.

Diferencie o que está realmente no DDL do que é apenas esperado pelo domínio.

## Composições paralelas

A análise anterior identificou composições paralelas para ficha e informação nutricional.

Determine:

- quais tabelas representam cada composição;
- se os mesmos ingredientes são duplicados;
- se as quantidades divergem;
- se a informação nutricional é calculada ou armazenada;
- se o rótulo pode se afastar da ficha;
- se há rastreabilidade entre elas;
- quais riscos de inconsistência existem.

A proposta da Panne deverá perseguir uma fonte técnica única e versionada, da qual cálculos e documentos sejam derivados.

## Informação nutricional

Investigue:

- base de cálculo;
- peso total;
- porção;
- rendimento final;
- medida caseira;
- nutrientes armazenados;
- kcal e kJ;
- percentual de valor diário;
- arredondamentos;
- ordem dos nutrientes;
- ingredientes declarados;
- alergênicos;
- glúten;
- lactose;
- validade;
- conservação;
- embalagem;
- peso líquido de venda;
- observações;
- responsável técnico;
- geração de PDF.

Marque como questão normativa qualquer comportamento que não possa ser validado apenas pelo DDL.

Não trate texto armazenado no legado como regra atual.

## Conceitos novos da Panne

Confronte o legado com os conceitos:

- `RecipeReference`;
- `Formulation`;
- `FormulationVersion`;
- `FormulationItem`;
- `ProcessStep`;
- `ScaleCalculation`;
- `Trial`;
- `TrialMeasurement`;
- `Approval`;
- `TechnicalProduct`;
- `NutritionCalculation`;
- `NutritionCalculationItem`;
- `TechnicalDocument`;
- `LabelSnapshot`;
- `CalculationEvidence`.

Para cada conceito, indique:

- correspondência no legado;
- ausência no legado;
- responsabilidade;
- relações;
- invariantes;
- necessidade de versionamento;
- escopo global ou organizacional.

## Regras fundamentais da proposta

A nova proposta deverá respeitar:

- formulações versionadas;
- versões publicadas imutáveis;
- cálculo determinístico;
- memória de cálculo;
- separação entre sugestão de IA e cálculo oficial;
- vínculo com versões específicas de ingredientes;
- nenhuma alteração retroativa;
- ficha técnica derivada da formulação;
- nutrição derivada de formulação e ingredientes versionados;
- rótulo como snapshot de dados, regras e fontes;
- aprovação como evento formal;
- distinção entre documento preliminar e aprovado;
- rastreabilidade de responsável, data e versão.

## Matriz de decisão

Produza:

### Preservar

Conhecimentos válidos do legado.

### Repensar

Conhecimentos úteis com modelagem inadequada.

### Descartar

Estruturas técnicas, duplicações e conceitos obsoletos.

### Criar

Versionamento, aprovação, evidência, grounding, conformidade e demais lacunas.

## Proposta PostgreSQL

Produza uma proposta sem implementação.

Para cada tabela, documente:

- nome;
- finalidade;
- colunas;
- tipos;
- precisão;
- PKs;
- FKs;
- checks;
- unicidades;
- índices;
- escopo organizacional;
- auditoria;
- versionamento;
- política de exclusão.

A proposta deve mostrar como as novas tabelas se relacionariam com:

- `organization`;
- `app_user`;
- `ingredient`;
- `ingredient_version`;
- `measurement_unit`;
- `nutrient_definition`;
- `allergen`;
- `data_source`;
- `audit_event`.

Não crie ainda o DDL executável.

## Questões obrigatórias

Classifique cada questão como:

- resolvida pelo DDL;
- inferência;
- decisão arquitetural;
- decisão do proprietário;
- decisão de especialista em panificação;
- decisão regulatória.

Inclua pelo menos:

- primeiro pão piloto;
- percentual do padeiro;
- farinha como base;
- pesos bruto e líquido;
- perdas;
- rendimento antes e depois do forno;
- ingredientes compostos;
- preparação usada como ingrediente;
- custo;
- porção;
- arredondamento;
- aprovação;
- revisão técnica;
- documento e rótulo;
- cálculo nutricional;
- normas e vigência.

## Documentos obrigatórios

Crie em `documentacao/legado/`:

- `DDL-FICHAS-PRODUTOS-INVENTARIO.md`;
- `DDL-FICHAS-PRODUTOS-RELACIONAMENTOS.md`;
- `DDL-NUTRICAO-INVENTARIO.md`;
- `DDL-NUTRICAO-RELACIONAMENTOS.md`.

Crie em `documentacao/arquitetura/`:

- `MATRIZ-LEGADO-FICHAS-E-NUTRICAO.md`;
- `MODELO-CONCEITUAL-FORMULACOES.md`;
- `MODELO-CONCEITUAL-NUTRICAO-E-DOCUMENTOS.md`;
- `PROPOSTA-POSTGRESQL-FORMULACOES.md`;
- `PROPOSTA-POSTGRESQL-NUTRICAO-E-DOCUMENTOS.md`;
- `QUESTOES-FICHAS-E-NUTRICAO.md`.

Inclua diagramas Mermaid das relações legadas e propostas.

Registre este prompt integralmente em `documentacao/prompts/`.

Registre o retorno em `documentacao/retornos/`.

## Critérios de aceite

- somente metadados e DDL consultados;
- nenhuma linha de negócio recuperada;
- nenhuma escrita no MySQL;
- nenhuma migração ou tabela PostgreSQL criada;
- produto polimórfico compreendido;
- composição da ficha compreendida;
- composição nutricional paralela compreendida;
- riscos de divergência identificados;
- modelo conceitual novo produzido;
- proposta PostgreSQL documentada;
- questões classificadas;
- nenhuma credencial registrada;
- nenhuma outra aplicação alterada.

## Retorno obrigatório

Entregue:

1. confirmação do modo somente leitura;
2. tabelas analisadas;
3. relações explícitas e inferidas;
4. funcionamento aparente do produto polimórfico;
5. estrutura da ficha técnica;
6. composição e preparo;
7. estrutura nutricional;
8. paralelismo entre ficha e rótulo;
9. regras valiosas;
10. fragilidades;
11. matriz resumida;
12. modelo conceitual proposto;
13. tabelas PostgreSQL propostas;
14. questões pendentes classificadas;
15. documentos criados;
16. `git diff --stat` e `git status --short`;
17. confirmação de ausência de leitura de dados;
18. confirmação de ausência de escrita;
19. confirmação de ausência de implementação antecipada;
20. riscos e recomendações.

Não avance para o `CURSOR-005`.

Aguarde a revisão do arquiteto.
