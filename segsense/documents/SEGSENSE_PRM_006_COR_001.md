# SEGSENSE_PRM_006_COR_001 — Correção única de integridade da governança

## Controle

- Projeto: SegSense
- Identificador: SEGSENSE_PRM_006_COR_001
- Versão: 1.1
- Data: 04/09/2026
- Corrige: SEGSENSE_PRM_006
- Natureza: único corretivo permitido para esta etapa

## Prompt para o Cursor

Aplique o único corretivo do `SEGSENSE_PRM_006` em `C:\Projetos\segsense`.

Leia integralmente `SEGSENSE_PRM_006`, `SEGSENSE_GOV_001`, `SEGSENSE_DAT_003`, `SEGSENSE_API_004`, `SEGSENSE_REV_006`, migrations V1–V5 e a implementação atual. Preserve todas as entregas funcionais aprovadas, inclusive as quatro correções herdadas do PRM_005.

Não altere V1–V5, pois já foram aplicadas. Não faça commit, push ou deploy. Não altere Spider, Panne, `.cursor/` ou qualquer caminho fora de `segsense/`.

## 1. Motivo da correção

A governança funciona na aplicação, mas a V5 não protege integralmente no PostgreSQL as relações que afirma modelar:

1. `contextual_opportunity.open_submission_id` referencia somente `opportunity_submission(id)`. Assim, SQL direto pode apontar uma oportunidade para a submissão de outra oportunidade.
2. `opportunity_decision.submission_id` e o par `(opportunity_id, revision_number)` possuem FKs independentes. Assim, uma decisão pode apontar para a submissão A e declarar oportunidade/revisão B.
3. `opportunity_submission` foi definida como parte da trilha imutável, mas a aplicação altera `status` de `OPEN` para `DECIDED`.
4. Os testes SQL atuais comprovam unicidade, mas não tentam os dois cruzamentos inválidos acima nem comprovam imutabilidade da submissão.

Essas falhas não autorizam reescrever a V5 nem apagar dados.

## 2. Migration corretiva V6

Crie `V6__harden_opportunity_governance_integrity.sql`.

Antes de adicionar constraints, a migration deve detectar e abortar explicitamente, sem corrigir ou apagar dados, se existir:

- `open_submission_id` ligado a submissão de outra oportunidade;
- decisão cujo `submission_id`, `opportunity_id` e `revision_number` não correspondam à mesma submissão;
- mais de uma decisão para a mesma submissão;
- referência a submissão ou revisão inexistente.

Depois, proteja no banco:

- adicione uma chave candidata nomeada em `opportunity_submission` que permita referenciar conjuntamente `id`, `opportunity_id` e `revision_number`;
- substitua a FK simples de `open_submission_id` por FK composta que obrigue o `open_submission_id` a pertencer à própria oportunidade; inclua a revisão se o modelo mantiver esse dado no aggregate e isso puder ser feito sem ambiguidade;
- substitua as FKs independentes da decisão por FK composta `(submission_id, opportunity_id, revision_number)` para a mesma linha de submissão;
- mantenha a unicidade de uma decisão por submissão;
- preserve `NO ACTION`, sem cascade e sem trigger de negócio;
- use constraints explicitamente nomeadas e índices adequados.

Não introduza correção automática de dados. Se a pré-validação encontrar inconsistência, Flyway deve falhar com mensagem técnica objetiva, sem mutação parcial.

## 3. Submissão realmente imutável

Pare de atualizar a linha de `opportunity_submission` após sua inserção.

Adote o seguinte modelo:

- a submissão é um fato imutável criado uma única vez;
- seu encerramento é representado pela inserção da `opportunity_decision`;
- a submissão atualmente aberta é aquela apontada por `contextual_opportunity.open_submission_id` e ainda sem decisão;
- ao decidir, insira a decisão e limpe atomicamente `open_submission_id` no aggregate;
- não use atualização de `status` da submissão como mecanismo de fechamento.

Como a V5 já existe, escolha uma evolução compatível:

- preserve a coluna histórica `status`, se removê-la aumentar o risco, mas pare de atualizá-la e documente sua depreciação; ou
- removê-la somente se a V6 puder fazê-lo com segurança e todos os mapeamentos/documentos forem ajustados.

Se `status` for preservada, novas submissões podem continuar registradas como `OPEN`, mas “aberta agora” deve ser derivado pelo ponteiro do aggregate e ausência de decisão — nunca pelo valor mutável dessa coluna. Remova ou substitua o índice parcial da V5 que impediria uma futura ressubmissão quando as linhas passarem a ser imutáveis.

Não use update ou delete em submissões, decisões ou eventos. A única mutação permitida continua sendo o estado corrente do aggregate na mesma transação das novas linhas append-only.

## 4. Aplicação e domínio

Ajuste repositórios e mapeamentos para:

- inserir a submissão uma única vez;
- nunca executar `UPDATE opportunity_submission`;
- localizar a submissão corrente pelo `open_submission_id` escopado à oportunidade;
- inserir exatamente uma decisão coerente com essa submissão;
- atualizar aggregate, inserir decisão e inserir evento na mesma transação;
- manter concorrência otimista e todos os códigos HTTP já aprovados;
- preservar segregação por sujeito, máquina de estados, janelas e disponibilidade efetiva.

Não amplie o escopo funcional.

## 5. Testes obrigatórios

Adicione testes PostgreSQL diretos que provem:

1. oportunidade A não pode apontar para submissão da oportunidade B;
2. decisão da submissão A não pode declarar oportunidade ou revisão B;
3. decisão coerente é aceita;
4. segunda decisão para a mesma submissão é rejeitada;
5. após `return-for-changes`, uma nova revisão e nova submissão são possíveis sem atualizar a primeira submissão;
6. a primeira submissão permanece byte a byte igual em seus campos persistidos depois da decisão;
7. falha concorrente não deixa decisão ou evento órfão;
8. V1–V6 sobem em banco vazio;
9. V6 aplica incrementalmente sobre V5 no volume existente sem apagar o volume.

Execute todas as regressões backend, frontend e ArchUnit. As quatro correções de UI do PRM_005 devem continuar testadas. Confirme 401 e correlação nas rotas reais sem IdP.

## 6. Documentação

Crie `SEGSENSE_PRM_006_COR_001.md` com cópia integral deste prompt.

Atualize:

- `SEGSENSE_DAT_003` para V6 e o relacionamento composto correto;
- `SEGSENSE_GOV_001` para esclarecer que submissão é fato imutável e decisão é outro fato;
- `SEGSENSE_REV_006` com achado, correção e provas;
- índice documental, README e histórico de versões afetados.

Não altere a referência normativa `SPIDER-ARCH-017`.

Registre que `.cursor/rules/ecosystem-focus.mdc` foi alterado na execução original apesar de estar fora de `segsense/`. Não tente restaurá-lo, apagá-lo ou modificá-lo neste corretivo sem conhecer com segurança seu conteúdo anterior. O corretivo deve produzir zero alterações novas fora de `segsense/`.

## 7. Critérios de aceite

- relações submissão–oportunidade–revisão–decisão inequívocas no PostgreSQL;
- submissões, decisões e eventos append-only na aplicação;
- nenhuma reescrita de V1–V5;
- V6 preventiva, incremental e sem correção destrutiva;
- ressubmissão válida após retorno para alterações;
- atomicidade, concorrência e segregação preservadas;
- testes SQL cobrindo explicitamente os cruzamentos antes permitidos;
- documentação indexada e coerente;
- nenhuma alteração nova fora de `segsense/`;
- nenhuma expansão para link, ContextInstance, Spider, Icatu ou mock.

## 8. Devolutiva obrigatória

Apresente:

1. diagnóstico confirmado das três falhas;
2. desenho final das FKs e chaves candidatas;
3. tratamento compatível da coluna `status` e do índice parcial da V5;
4. comprovação de que submissão não sofre mais UPDATE;
5. provas SQL dos cruzamentos rejeitados;
6. prova de ressubmissão e preservação da primeira submissão;
7. migrations V1–V6 e aplicação incremental da V6;
8. testes e builds completos;
9. HTTP real 200 público e 401 correlacionado nas novas rotas;
10. arquivos e documentação;
11. estado Git e confirmação de zero novas alterações externas;
12. ausências preservadas.

Não faça commit, push ou deploy.
