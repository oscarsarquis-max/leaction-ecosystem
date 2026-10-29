# ISA 007A — Conexão bancária pela Pluggy

Data: 27/10/2026. Base de código: isa-piloto 0.6.18, schema 12, que passa a migrar para o schema 13. A imagem de produção não foi trocada.

A pessoa padrão continua sendo a Eveline. Este recorte não desenha as telas dela. Ele traz a conexão do proprietário, com o Meu Pluggy, e um acesso provisório na lista de Contas.

## O que o proprietário ainda precisa fazer

O Cursor não cria a conta, não liga o conector e não lê o segredo. Antes de publicar:

1. Criar a conta em [meu.pluggy.ai](https://meu.pluggy.ai) e conectar lá os bancos.
2. Criar uma aplicação em [dashboard.pluggy.ai](https://dashboard.pluggy.ai).
3. Ativar o conector MeuPluggy nessa aplicação.
4. Guardar `clientId`, `clientSecret` e um `webhookSecret` no AWS Secrets Manager, num segredo só da ISA. O JSON usa essas três chaves. Nada disso entra no repositório, no chat ou num `.env` versionado.
5. Informar o nome do segredo.

Sem o nome do segredo não há ensaio no sandbox, nem prova com os bancos reais, nem registro do webhook, nem imagem 0.7.0.

## Investigação

Onde a página não diz, fica registrado como não documentado. Nada disso foi completado por suposição.

### Autenticação

Fonte: [Authentication](https://docs.pluggy.ai/reference/authentication) e [Create API Key](https://docs.pluggy.ai/reference/auth-create).

- `POST https://api.pluggy.ai/auth` recebe `clientId` e `clientSecret` e devolve `apiKey`.
- O cabeçalho das chamadas seguintes é `X-API-KEY`.
- A API key vale 2 horas e alcança todos os endpoints. Fica só no servidor.
- `POST /connect_token` recebe a API key e devolve `accessToken`, válido por 30 minutos.
- `clientUserId` e `webhookUrl` vão dentro de `options`. Na raiz do corpo, `clientUserId` é descartado e a chamada ainda responde 200.
- O connect token só enxerga o item criado com ele. Não substitui a API key.

### Widget

Fonte: [Introduction](https://docs.pluggy.ai/docs/connect-widget/introduction) e [Authentication](https://docs.pluggy.ai/docs/connect-widget/authentication).

- O navegador recebe só o connect token. `clientId` e `clientSecret` não podem aparecer na página.
- `onSuccess` devolve o item. No exemplo React, o id está em `item.id`. No exemplo JavaScript, o argumento é o dado do item. A tela aceita os dois formatos e envia `item.id`.
- `onError` recebe a mensagem e, quando existe, o item.
- O pacote npm `pluggy-connect-sdk` 2.14.2 publica `dist/main/index.js`, que não é o arquivo de navegador. `https://cdn.pluggy.ai/pluggy-connect/v2.14.2/pluggy-connect.js` respondeu 404 em 27/10/2026. O arquivo de navegador mais novo que respondeu 200 foi `https://cdn.pluggy.ai/pluggy-connect/v2.11.0/pluggy-connect.js`. Essa é a versão fixada. O construtor no arquivo é `PluggyConnect`, com `init()`.

### Item

Fonte: [Personal use](https://docs.pluggy.ai/docs/guides/meu-pluggy-personal-use) e a página de webhooks.

- O item do Meu Pluggy espelha a conexão feita em meu.pluggy.ai. A atualização é automática a cada 24 horas e não pode ser forçada pela API.
- `GET /items/{id}` devolve `consentExpiresAt`. A autorização do Meu Pluggy dura um ano. Depois disso as leituras voltam vazias e a próxima atualização vai para `LOGIN_ERROR` com `USER_AUTHORIZATION_EXPIRED`, disparando `item/error`.
- Renovar é conectar o MeuPluggy de novo no Demo. A documentação pede para não assumir que o `itemId` continua o mesmo.
- `GET /v2/items` não existe para conta Meu Pluggy. Por isso o `itemId` é gravado no sucesso do widget.
- `item/waiting_user_input` espera um dado do usuário. `item/waiting_user_action` espera uma aprovação no aparelho, como autorizar no aplicativo do banco. Os dois estados pedem a mesma frase na ISA: "É preciso autorizar de novo no seu banco."
- A lista fechada de `executionStatus` transitórios não foi relida nesta entrega. O que a sincronização grava é o `status` do item e, quando existe, o código em `error.code` ou o `executionStatus`. Não grava a mensagem livre do provedor.

### Contas

Fonte: [Account](https://docs.pluggy.ai/docs/products/accounts).

- Tipos documentados: `BANK` / `CHECKING_ACCOUNT`, `BANK` / `SAVINGS_ACCOUNT`, `CREDIT` / `CREDIT_CARD`.
- `balance` da conta bancária é o valor disponível. Negativo é dívida, por exemplo cheque especial. Não há campo de data desse saldo.
- `bankData.transferNumber` é COMPE / agência / conta. `closingBalance` não é o saldo do dia anterior.
- No cartão, `balance` é a fatura aberta ainda não paga. `creditData.balanceDueDate` é o vencimento, `balanceCloseDate` é o fechamento e `minimumPayment` é o mínimo. Os três existem na documentação.
- `owner` e `taxNumber` vêm na conta. A ISA não os grava.

Não documentado: a data do saldo da conta corrente ou da poupança. Sem essa data, a ISA não grava `availability`. Gravar o dia da sincronização seria tratar "saldo atual" como "saldo de hoje" sem a fonte dizer isso. O rótulo "Disponível hoje" continua valendo só quando a data do saldo é a data de referência.

### Transações

Fonte: [Transaction](https://docs.pluggy.ai/docs/transactions) e a [listagem por página](https://docs.pluggy.ai/reference/transactions-list).

- A fonte recupera até 12 meses.
- `type` `DEBIT` é saída e `CREDIT` é entrada.
- No cartão, valor positivo é despesa e valor negativo é pagamento. A ISA usa `type`. Se `type` não vier, essa convenção de sinal só é aplicada em conta `CREDIT`. Sem `type` numa conta `BANK`, o lançamento não entra.
- `status` `POSTED` está liquidado. `PENDING` ainda não liquidou. Só `POSTED` entra, como realizado (`pago` ou `recebido`).
- `date` é ISO 8601 em UTC. Para ler como horário do Brasil, a documentação manda converter para GMT-3. A data civil gravada é o dia em `America/Sao_Paulo`.
- O id estável do lançamento é `id`. `providerId` existe só em conector de Open Finance e serve para reconhecer o mesmo lançamento quando o id muda. A ISA guarda os dois e, se o `providerId` já estiver num lançamento da mesma conta, atualiza esse lançamento em vez de criar outro.
- A listagem por página documenta `from`, `to`, `page` e `pageSize` (máximo 500) e segue disponível até 31/12/2026. O guia manda usar cursor. A ISA chama `GET /v2/transactions` com `accountId`, `from` e `to`. Se o corpo trouxer `next`, segue esse endereço. Se trouxer `page` e `totalPages`, percorre as páginas.
- Não documentado nesta releitura: a lista de parâmetros do `GET /v2/transactions` em página própria. A URL consultada devolveu o endpoint antigo. `from` e `to` são os parâmetros documentados na listagem por página e no exemplo `GET /transactions?from=&to=`.
- `category` depende do plano Pro e pode vir nula. No Meu Pluggy isso não está garantido. Quando vem, vai para `payload.pluggyCategory`.

### Investimentos

Fonte: [List investments](https://docs.pluggy.ai/reference/investments-list).

- A consulta filtra `type` em `COE`, `EQUITY`, `ETF`, `FIXED_INCOME`, `MUTUAL_FUND`, `SECURITY` e `OTHER`. A paginação é `page` / `pageSize`.
- O exemplo traz `balance`, `currencyCode`, `date`, `type` e `subtype`. A posição usa `balance` e a data civil de `date`.
- Não documentado: um campo de resgate ou de liquidez. O exemplo mostra `amountWithdrawal` sem dizer que isso é liquidez. `liquidity_note` fica nulo. A posição não vira lançamento e não entra no que pode gastar.

### Webhooks

Fonte: [Webhooks](https://docs.pluggy.ai/docs/webhooks).

- Eventos lidos: `item/created`, `item/updated`, `item/error`, `item/waiting_user_input`, `item/waiting_user_action`, `transactions/created`, `transactions/updated`, `transactions/deleted`.
- `clientUserId` vem nos eventos `item/*`. Nos eventos de transação a ISA acha a pessoa pelo `itemId` já gravado.
- Entrega: 2xx em até 10 segundos. Até 3 tentativas. `400`, `401`, `403`, `404` e `405` não são repetidos.
- Cabeçalhos customizados só existem no `POST /webhooks`, com o objeto `headers`. Não aparecem no painel. O cabeçalho da ISA é `X-ISA-Bank-Secret`.
- `transactions/created` traz `createdTransactionsLink`. `transactions/updated` traz `transactionIds`. `transactions/deleted` traz só os ids. A documentação diz para apagar; a ISA marca `originRemoved` e conserva o lançamento, como este prompt pediu.
- Um id pode mudar quando data, descrição ou valor mudam demais. Não há campo ligando o id antigo ao novo. A reconciliação documentada é `providerId` ou, na falta dele, data, valor e descrição.

### Meu Pluggy e o plano pago

Fonte: [Personal use](https://docs.pluggy.ai/docs/guides/meu-pluggy-personal-use).

- Uso pessoal, gratuito, sem due diligence, até 5 conexões, sem uso comercial.
- O mesmo titular é a pessoa que conectou os próprios bancos no Meu Pluggy. A página não documenta um campo de CPF para a ISA conferir. A trava da ISA é a lista `ISA_PLUGGY_ALLOWED_SUBS`, não uma checagem de CPF.
- `GET /v2/items` indisponível. Atualização a cada 24 horas, sem atualização manual.
- O plano pago, para outras pessoas, é a integração regular, com conversa comercial. Não está habilitado no código.
- O sandbox é outro conector, com dados sintéticos. A conexão Meu Pluggy é dado real.
- Não documentado: o limite de 100 itens no ambiente de desenvolvimento. Não apareceu na página de uso pessoal nem nas páginas relidas em 27/10/2026.

### Conta digitada e extrato já importado

A documentação da Pluggy não fala da ISA. As regras abaixo são da ISA.

Conta manual: mesma pessoa, mesma moeda, mesmo COMPE, mesma agência quando os dois lados têm agência, e o número, só com dígitos, coincide. Se houver um único candidato, a conta ganha `external_id`, `provider`, `bank_link_id`, `external_type` e `external_subtype`. A moeda não muda. O `change_log` registra `conta-vinculada-banco`. Dois candidatos: a ISA não escolhe e não cria outra conta.

Extrato BB: mesma conta, mesma data civil, mesmo valor absoluto, mesma direção (`entrada` ou `saida`) e texto compatível. O texto da Pluggy e o do lançamento, ou a `lineSignature`, são reduzidos a letras e números. Um contém o outro e os dois têm pelo menos 8 caracteres. A origem continua `extrato-bb-arquivo`. O `external_id` é preenchido e `pluggyCategory` é guardado. O `change_log` registra `lancamento-vinculado-banco`. Dois candidatos no mesmo dia e valor: o lançamento da Pluggy não entra, para não duplicar nem fundir compras diferentes.

## Schema 13

Migração só aditiva, em `store._migrate_body`, quando `version < 13`.

| Peça | O que acrescenta |
|---|---|
| `bank_link` | `id`, `owner_id`, `provider`, `item_id` único, `connector_name`, `status`, `status_detail`, `consent_expires_at`, `last_synced_at`, `created_at`, `updated_at`. Índice por `owner_id`. |
| `account` | `external_id`, `provider`, `bank_link_id`, `external_type`, `external_subtype`. `cartao` entra em `ACCOUNT_KINDS`. |
| `investment_position` | `id`, `owner_id`, `bank_link_id`, `external_id`, `name`, `kind`, `amount_cents`, `currency`, `as_of`, `liquidity_note`, `raw_json`, `updated_at`. Índice por `owner_id` e único `(owner_id, external_id)`. |
| `ledger_entry` | `external_id`. Índice único `(owner_id, external_id)` quando o valor não é nulo. |
| `bank_event` | `event_id` único, `owner_id`, `event`, `item_id`, `received_at`, `processed_at`, `status`, `error_code`, `payload_json`. Índice por `owner_id`. `payload_json` guarda só ids e o link da página, para o processamento posterior. |

`owner_id` em `bank_event` não estava na lista mínima do prompt. Sem ele a exclusão da pessoa não alcançava o evento. A coluna é nula quando o item ainda não tem vínculo.

Quem já gravava conta e lançamento continua gravando. As colunas novas nascem nulas. O teste `test_schema_keeps_prior_writers` confirma a linha do schema 12, um segundo migrate sem apagar contas, e `external_id` nulo num lançamento antigo. Os testes de lançamento antigo (`velho` e `velho-13`) continuam preenchendo as colunas do 005T5 sem reescrever o JSON. Com isso, a 0.6.18 consegue ler e inserir sobre o schema 13. A troca, quando for publicada, pode ser contínua. O retorno é a revisão `isa-web:27`.

O cartão fica fora do que pode gastar, no mesmo lugar em que o investimento sem liquidez já ficava. A fatura entra como compromisso. Isso não altera o cenário de 26/10, que não tem cartão.

## O que mudou por arquivo

| Arquivo | Mudança |
|---|---|
| `server/pluggy.py` | Cliente. Chave em cache por 2 horas, renovada 5 minutos antes. Tempo limite de 8 segundos e no máximo uma nova tentativa, em tempo esgotado ou resposta 5xx. |
| `server/banksync.py` | Trava, token, vínculo, sincronização, webhook, desligar e a frase pública. |
| `server/store.py` | Schema 13, `cartao`, `external_id` escrito só por `write_entry`, exclusão das tabelas novas e do item remoto antes de apagar a pessoa. |
| `server/wsgi_app.py` | `POST /api/bank/webhook` sem sessão. Demais rotas `/api/bank/` exigem a pessoa e a lista. A lista de contas ganha `bankConnect` e `bankLinks`. |
| `server/serve.py` | O mesmo no laboratório. |
| `server/prod_serve.py` | O processo de fundo só sobe com `ISA_PLUGGY_ENABLED=1`. Uma conexão, fora do pool dos pedidos. |
| `server/test_banco_007a.py` | Respostas gravadas, em SQLite e num PostgreSQL isolado. |
| `prototype/app.js` | Botão "Conectar banco" e a lista de vínculos, só quando `bankConnect` é verdadeiro. |
| `scripts/ops/register-pluggy-webhook.py` | Registra o webhook com o cabeçalho. Não imprime o segredo. Ainda não foi executado. |
| Testes de schema | A versão máxima esperada passou de 12 para 13. A linha do schema 12 continua lá. |

Variáveis: `ISA_PLUGGY_ENABLED`, `ISA_PLUGGY_SECRET_NAME`, `ISA_PLUGGY_ALLOWED_SUBS`. Sem a primeira, ou fora da lista, a API responde 403: "A conexão com bancos ainda não está disponível para a sua conta." O botão não é desenhado. Em produção a lista é de `sub` do diretório. No laboratório, a identidade sintética.

`clientUserId` é o SHA-256 do `owner_id`. Não é e-mail. O `POST /api/bank/links` recusa item de outra aplicação (a API responde 404 para item alheio) e item cujo `clientUserId` não é o da pessoa.

A tela diz "Conectando… pode levar alguns minutos" e não espera a sincronização. O trabalho entra em `bank_event` e corre no processo de fundo.

## Correspondência de categorias

A categoria da Pluggy fica em `payload.pluggyCategory`. A categoria da ISA só é preenchida quando o nome está nesta tabela, com `categorizationStatus = "sugerida"`. Não fica confirmada. A IA da ISA pode sugerir depois. Nome desconhecido fica em "a categorizar".

| Categoria da Pluggy | Categoria da ISA |
|---|---|
| Groceries, Eating out, Food and drinks | Alimentação |
| Rent, Housing, Utilities | Moradia |
| Transportation, Transport | Transporte |
| Healthcare, Health, Pharmacy | Saúde |
| Education | Educação |
| Entertainment, Video streaming, Leisure | Lazer |
| Shopping | Compras |
| Salary, Income | Salário |
| Services | Serviços |

Transferência e investimento não entram na tabela. Chamar isso de "Outros" seria escolher por ela.

## Sincronização

Primeira leitura de uma conta: de 365 dias antes da data de referência até essa data. A documentação diz "até 12 meses" e não fixa o dia. Depois: desde a última data já gravada, com 7 dias de sobreposição. `external_id` repetido não cria outro lançamento; atualiza o que já existe.

A fatura aberta vira um compromisso `origin = "banco"`, ligado à conta do cartão, identificado por `conditions.pluggyOpenBill`. A sincronização seguinte atualiza a mesma linha. Mínimo e vencimento entram quando a API os manda.

Moeda diferente de Real, dólar e euro é guardada no código da conta, sem conversão. O grupo de moeda que a lista já faz continua valendo.

Posição de investimento não gera lançamento. Sem nota de liquidez, fica fora do que pode gastar.

Uma lista vazia, por consentimento vencido, não apaga contas nem lançamentos.

A reserva diária lê os vínculos que não estão desligados e cuja última sincronização é anterior ao dia civil anterior. Não pede à Pluggy para atualizar o item, porque o Meu Pluggy não aceita atualização manual.

## Desligar e excluir

"Desligar este banco" apaga o item na Pluggy, marca o vínculo como desligado e mantém contas, lançamentos, faturas e posições.

`forget_owner` pede a remoção dos itens antes de apagar os dados locais. Falha nessa chamada é registrada pelo tipo do erro e não impede a exclusão local.

Um `transactions/deleted` não apaga a linha. Marca `originRemoved`.

## Testes

Suíte Python completa, SQLite e PostgreSQL isolado em `127.0.0.1:5442`. Protótipo: `ui`, `calc`, `lotes`, `bb-statement` e `regras-mes`. O cenário de 26/10 e as regras do 005T5 permanecem os mesmos números; a suíte que os cobre voltou a passar depois do schema 13.

Acrescentados, com respostas gravadas e sem chamada real:

1. Cache da chave, expiração às 2 horas, 401 sem segunda tentativa, tempo esgotado com uma nova tentativa, 500 com uma nova tentativa.
2. Pessoa fora da lista recebe 403 e o código da tela só desenha "Conectar banco" quando `bankConnect === true`.
3. `itemId` com outro `clientUserId` não grava vínculo.
4. Sincronização inicial: conta manual vinculada, cartão, três lançamentos realizados, pendente de fora, uma fatura, uma posição. A segunda sincronização não aumenta essas contagens. A janela pedida na segunda vez começa 7 dias antes da última data.
5. Extrato BB com a mesma data, o mesmo valor e a descrição compatível fica com o `external_id` e conserva a origem do arquivo.
6. Webhook sem cabeçalho responde 401 e não grava. Repetido, uma linha. A aceitação, sem processar, ficou abaixo de 1 segundo. "Deleted" conserva o lançamento. `item/error` muda o estado para a frase de autorizar de novo.
7. Desligar conserva o histórico e chama `DELETE` do item. A exclusão da pessoa também chama `DELETE`. O livro de exclusões do teste é um arquivo temporário, para não marcar `pessoa-teste` no livro local.
8. A saída do processo, durante a sincronização, não contém o segredo, a chave, o nome, o documento, o valor 9876.54 nem o `itemId` completo.
9. No PostgreSQL isolado, o schema sobe e o mesmo `eventId` é aceito uma vez. Cabeçalho errado responde 401.

O saldo da conta corrente passou a ser gravado no R1, com a data de `lastUpdatedAt`.

## Ensaio no sandbox

Não executado. Falta o segredo e uma aplicação com o conector de sandbox. Quando o nome do segredo existir, o ensaio é: conectar o banco de teste pelo acesso provisório, sincronizar, receber um webhook em `https://isa.actionhub.com.br/api/bank/webhook` com o cabeçalho, e desligar esse item de teste. O script `scripts/ops/register-pluggy-webhook.py` faz o registro e não imprime o segredo.

## Prova real

Não executada. Quando o proprietário conectar pelo acesso provisório, o relatório deve mostrar só contagens: contas por tipo, transações por mês, posições, faturas viradas em compromisso e eventos recebidos. A segunda sincronização não pode aumentar essas contagens. "Desligar" fica para um banco de teste se houver dúvida sobre um banco real.

## Publicação e retorno

Não publicada. A produção continua em `isa-web:27`, isa-piloto 0.6.18, schema 12, imagem `sha256:c88927d1e966cadf485311e7d66f98f19072d47961a63fbaf09f4e9127a61256`.

Quando o segredo for informado, a ordem é: cópia, `VERSION` isa-piloto 0.7.0, imagem, commit só deste recorte, push sem force, revisão nova da tarefa com o segredo montado e a permissão do papel limitada a ele, registro do webhook, prova por contagens. O retorno é `isa-web:27`. O `VERSION` não foi adiantado para 0.7.0 justamente porque a imagem não saiu.

O schema 13, e a coluna `observed_at` do schema 14, já estão no código. Quem subir este código migra ao iniciar. A 0.6.18 segue inserindo sobre essas colunas nulas, então a ida pode ser contínua. O retorno da aplicação para a 0.6.18, com o schema já à frente, também lê e insere, porque a migração antiga vê a versão atual e para, e os inserts nomeiam as colunas.

## Limitações

- Corrente e poupança usam `lastUpdatedAt` do item como data do saldo. Sem esse campo, o saldo não é gravado.
- Liquidez de investimento não é lida. A posição fica fora do que pode gastar.
- Categoria da Pluggy pode não vir no Meu Pluggy. A sugestão da ISA só nasce quando o nome está na tabela.
- O filtro de datas do `GET /v2/transactions` não teve página própria. A chamada usa `from` e `to` documentados na listagem por página.
- O limite de 100 itens do ambiente de desenvolvimento não foi encontrado.
- O arquivo de navegador fixado é o 2.11.0, não o 2.14.2 do npm, porque o 2.14.2 não está nesse endereço da CDN.
- Webhook sem o cabeçalho recebe 401, e a Pluggy não repete 401. O registro pela API, com o cabeçalho, é obrigatório antes do uso real. O `webhookUrl` do token não documenta cabeçalho.
- Não há telas da Eveline, plano pago, Pix, conversão de moeda, nem mudança em ActionFinance, Cognito, Spider ou Hub.

## R1

Ajustes antes de publicar. A imagem continua `isa-web:27`, isa-piloto 0.6.18. O `VERSION` não mudou.

### Saldo e hora da última atualização

O objeto Item, em [Retrieve](https://docs.pluggy.ai/reference/items-retrieve), traz `lastUpdatedAt` no exemplo de uma atualização concluída: `"status": "UPDATED"`, `"executionStatus": "SUCCESS"`, `"lastUpdatedAt": "2024-09-19T13:11:23.595Z"`. É um instante, não só um dia. A página de ciclo de vida diz que `UPDATED` significa que a última sincronização terminou e os dados podem ser lidos.

A ISA grava `availability` com `source = "banco"` só quando esse campo vem preenchido. `as_of` é a data civil em `America/Sao_Paulo`. A hora fica em `observed_at`, coluna nova e nula, schema 14. Sem `lastUpdatedAt`, a hora da sincronização da ISA não entra.

"Disponível hoje" continua só quando essa data é a data de referência. Saldo negativo é gravado negativo. A linha não conta como dinheiro que cobre o dia.

A leitura, sem tela nova, está em `store.freshness_label`:

- mesmo dia: "atualizado às HH:MM";
- dia anterior: "atualizado ontem às HH:MM";
- mais antigo: "atualizado em DD/MM".

### Cartão no motor, antes e depois

Antes, uma compra no cartão entrava no realizado do mês (`month_picture` e `calc.summarize`) porque era lançamento `pago` de consumo. A fatura, gravada como compromisso, entrava de novo no previsto do mês. As duas somas juntas dobravam o gasto. O motor de projeção (`engine.py`) não lia os lançamentos: só compromissos, entradas e reservas. A composição de gastos (`lotes.js` e `workbatches.py`) lia os lançamentos e não lia a fatura.

Depois:

| Onde | Compra no cartão | Fatura |
|---|---|---|
| Gastos e categoria | Conta | Não conta |
| Dinheiro do mês | Não conta | Conta, pelo `remaining_cents` |

Três compras de R$ 100, R$ 120 e R$ 80 e uma fatura de R$ 300 dão R$ 300 de saída no mês, não R$ 600. A semana dessas compras soma R$ 300 em Alimentação.

### Pagamento da fatura

Não havia um par de transferência entre a corrente e o cartão. A natureza `transferencia` já existia e já fica fora dos gastos e do resultado do mês. O R1 usa essa natureza.

O par é uma saída na corrente ou na poupança e um crédito na conta `cartao`, da mesma pessoa, do mesmo valor, com até 3 dias de diferença. Os dois recebem `nature = "transferencia"` e `transferPair` com o id do outro. Não contam em gastos nem no dinheiro do mês.

A fatura aberta dessa conta, `origin = "banco"`, reduz o restante pelo valor pago. Pagamento integral zera o restante. Pagamento menor deixa o restante na mesma conta a pagar. Não nasce outra.

Crédito no cartão sem a saída correspondente vira `pagamento_fatura`. Conta uma vez no dinheiro do mês, como saída, e não entra nos gastos. O restante da fatura continua na mesma conta a pagar.

### Vínculo um a um

O texto compatível continua o mesmo: um lado contém o outro, os dois com pelo menos 8 letras ou números. O que mudou é o empate. Antes, dois candidatos no mesmo dia e valor faziam o lançamento da Pluggy não entrar. Agora os pares são escolhidos do mais parecido para o menos, e o empate segue a ordem de chegada. O que sobrar é criado.

O caminho inverso está em `plan_import_links`, chamado por `import_batch`. Um extrato do Banco do Brasil importado depois da conexão grava a assinatura no lançamento que já veio da Pluggy e não cria outra linha. A origem desse lançamento continua `pluggy`.

### Testes novos

- Saldo com `lastUpdatedAt` às 07:40, e ausência de saldo quando o campo não vem.
- Saldo negativo fora do que cobre o dia. Rótulos de hoje, ontem e data antiga.
- Três compras e uma fatura: R$ 300 no mês e R$ 300 na categoria.
- Par marcado como transferência, fatura zerada, e o mês sem contar duas vezes.
- Pagamento parcial de R$ 100 numa fatura de R$ 300: resta R$ 200 na mesma conta a pagar, uma só, e o mês soma R$ 300.
- Pagamento sem par não entra nos gastos.
- Dois lançamentos do extrato e três da Pluggy, no mesmo dia e valor: dois vínculos e o terceiro criado.
- Extrato importado depois: os dois lançamentos da Pluggy recebem a assinatura e a contagem não sobe.

As suítes anteriores continuam, inclusive o cenário de 26/10 e as regras do 005T5. Nada foi publicado.
