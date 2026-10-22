# ACTIONFINANCE_REV_DADOS_CONTAS_054

22/10/2026. Dados cadastrais da conta e configuração de acesso. Implementado no ActionFinance. A ISA não foi alterada.

Esta primeira etapa ficou na árvore de trabalho e não publicou. O fechamento publicado está em [ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md](ACTIONFINANCE_REV_PUBLICACAO_CONTAS_054R1.md).

## Estado conferido antes da mudança

O código e o changelog locais estão em **0.2.10**, schema **V24**. A task publicada citada no relato 053 é `actionfinance-web:27`, com Flyway desligado na task web. Esta entrega **não publica** e **não numera** uma versão nova: o site em produção continua o que já estava no ar. A Conta Mercado Pago produtiva não foi preenchida nem substituída.

## O que a pessoa passa a ver

Tesouraria → Contas → Abrir abre em **Dados da conta**. O cabeçalho tem o retorno a Contas, o nome, a empresa, a situação, **Editar dados** e **Ver extrato**. As abas ficam na URL (`aba=movimentos` ou `aba=acesso`; a ausência de `aba` é Dados da conta). Voltar do extrato recupera a aba de origem daquela conta.

Conta antiga sem identificação bancária mostra **Não informado** e **Complete os dados desta conta**. O apelido não vira banco, número, modalidade nem titularidade. Movimentos e extratos antigos continuam consultáveis.

Cadastro bancário novo exige banco ou instituição, número da conta e modalidade (corrente, poupança, investimento ou conta de pagamento). Apelido, país, código, agência e contatos ficam em **Mais informações**. Sem apelido, o nome gravado usa a instituição e o número mascarado. O número `0012345-6` permanece texto. Caixa físico pede nome e não pede dados bancários. A moeda exibida é **BRL · Real**. O início do controle não é a abertura no banco e não é regravado ao editar o cadastro. Saldo inicial continua opcional e separado: em branco, a posição segue **Não apurada**.

**Gerenciar conta** saiu. Inativar ou reativar fica em **Situação da conta**. Leitura não exige permissão de escrita; o servidor continua exigindo escrita para gravar.

**Acesso e importação** separa arquivo e conexão. Os formatos citados são os que o Finance já lê: liquidação Mercado Pago (CSV com ponto e vírgula) e CSV de laboratório. **Conexão automática ainda não disponível.** Nenhum seletor se declara conectado. Vínculos de origem já gravados aparecem pela procedência, sem pedir o identificador técnico.

Investimento é modalidade de cadastro. O resumo da Tesouraria não foi alterado e não passa a tratar essa posição como dinheiro disponível.

## Persistência

Migration aditiva `database/migrations/V25__account_registration.sql`. Não reescreve V1–V24. Colunas novas nascem nulas. Contatos ficam em `financial_account_contact`, com escopo de empresa e substituição lógica (`removed_at`), sem apagar a linha. A trilha usa `PROFILE_UPDATED` e guarda o número mascarado e a quantidade de contatos, não o número completo nem o e-mail do contato.

O tipo interno continua `BANK`, `CASH` ou `OTHER`. A modalidade é outro campo. Moeda continua restrita a BRL. Idempotência e versão cobrem o conteúdo novo. Outra empresa ou ausência de permissão continua recusada pelos controles já existentes de escopo.

## Ensaio isolado

Postgres 17.6 descartável, sem usar o banco local da porta 5439 nem o banco de produção. Flyway até V24, carga sintética identificada como ensaio, depois V25.

| Leitura | Antes | Depois da V25 | Restauração do dump |
|---|---|---|---|
| Conta `44444444-4444-4444-8444-444444444444` | Conta ensaio legado, BANK, versão 1 | O mesmo id, nome, tipo e versão | O mesmo id e nome |
| Identificação bancária | Colunas ainda não existiam | Nula | Nula |
| Soma dos movimentos | 7000 | 7000 | 7000 |
| Títulos / baixas / soma das baixas | 1 / 1 / 7000 | 1 / 1 / 7000 | Preservados no dump restaurado |
| Lotes / linhas / vínculos | 1 / 1 / 1 | 1 / 1 / 1 | Restaurados com o schema V25 |
| Contatos | — | 0 | 0 |

O container do ensaio foi removido ao final. Nada disso foi aplicado em produção.

## Prova de código

- `AccountProfileRulesTest`: número literal, máscara, caixa sem dados bancários, conta bancária antiga em branco e recusa de dois contatos principais.
- Compilação do backend, inclusive os testes.
- Interface: criação no diálogo e na página, edição com a mesma chave após falha de resposta, aba Dados da conta com ausências explícitas, movimentações com posição e zero informado. `tsc --noEmit` limpo.
- Um teste antigo de título (`retries a create with the same key after a lost transport response`) continua falhando porque a descrição aparece no título da página e de novo em Dados do título. Essa tela não faz parte desta entrega.

## O que esta entrega não conclui

Não há captura de navegador em 1440, 1280, 768, 390, 360 nem zoom de 200%. Não houve sessão autenticada no ambiente publicado. Não houve backup nem migration de produção. Flyway não foi ligado na task web. Aceite do proprietário não ocorreu e não está sendo atribuído.

A publicação fica para o ciclo seguinte, com backup, migration controlada da V25 e prova autenticada. Até lá, quem abre Contas no ar ainda vê a tela anterior.
