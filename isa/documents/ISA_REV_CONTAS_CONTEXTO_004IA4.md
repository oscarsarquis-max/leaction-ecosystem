# ISA 0.6.5 — Contas e contexto

19/10/2026. Evolução da 0.6.4. O schema passa a 5. A base, as identidades e o serviço continuam os mesmos.

## Modelo

A tabela `account` existente ganhou instituição, tipo, forma de entrada, situação, liquidez e atualização. Não há um segundo cadastro. Os tipos são conta corrente, poupança e investimento. As moedas aceitas são BRL — Real, USD — Dólar americano e EUR — Euro, todas com duas casas decimais. Outra moeda é recusada. Não há cotação nem total convertido.

Conta sem saldo informado mostra “Não informado”. Compromisso antigo sem `account_id` permanece sem conta definida e não é atribuído à primeira conta. O disponível antigo, também sem conta, continua sendo a posição da pessoa. Ele não é copiado para cada conta e não é somado com um disponível já gravado numa conta. Atribuição pede prévia e confirmação; repetir não muda valor, data nem origem.

Conta de investimento sem liquidez fica fora da margem. O arquivo CSV do Banco do Brasil só entra numa conta ativa em Real. Uma conta em outra moeda aceita lançamento manual e informa que não há leitor compatível. Não há conexão bancária nem pedido de senha.

## O que a escolha muda

O cabeçalho tem o nome da pessoa, o seletor Conta e Sair. A preferência fica por proprietário. Sem preferência, a visão é Todas as contas. Conta inativa ou de outra pessoa volta para Todas, com aviso. Início, lançamentos, planejamento, calendário e leitura usam o mesmo contexto, validado no servidor. O navegador não escolhe o proprietário.

Em Todas, moedas diferentes aparecem separadas, sem um total em reais. Numa conta, compromissos sem vínculo ficam de fora e a frase diz quantos são. A leitura de uma conta não reaproveita a leitura de outra. Sair encerra a sessão da ISA. Se o diretório publicar `end_session_endpoint`, o navegador segue esse endereço; sem ele, a sessão da ISA termina e a sessão do provedor depende do que o diretório expõe.

Perfil deixa de se chamar conta financeira. Importar extrato permanece em Início, Lançamentos e no detalhe da importação. O texto de privacidade descreve Claude via AWS, a gravação de sugestões e os sete dias como retenção da cópia.

## Verificação de laboratório

SQLite temporário e PostgreSQL isolado em `127.0.0.1:5442`, com bases descartáveis. Não é a conta publicada.

A migração 5 preserva compromisso e valor sem conta. Corrente e poupança em Real, conta em dólar, inativação e moeda travada depois do uso foram conferidas. A visão de uma conta não herda o disponível pessoal nem o compromisso da outra moeda. A importação em Real é recusada na conta em dólar. Investimento sem liquidez não completa a margem. Outra pessoa não usa o id da conta. A preferência de uma não altera a da outra. A cópia de diretório leva a moeda e a preferência.

No navegador de laboratório, Paulo cadastra Corrente em Real e Viagem em dólar, alterna o seletor e vê as moedas separadas, sem R$ 0,00 no lugar de dado ausente. Sair está no cabeçalho e volta à entrada. Em 360 px a barra não estoura e Sair continua visível. Capturas em `documents/reviews/contas-004ia4/`.

## Publicação

Servida em https://isa.actionhub.com.br como isa-piloto 0.6.5, task isa-web:14, no serviço isa já existente. Saúde 200, base postgres, Claude no Bedrock. `/api/ready` responde schema 5. `/api/workspace` sem sessão responde 401. O `app.js` servido traz o seletor “Todas as contas” e o botão Sair.

A imagem registrada é o índice `sha256:ea67ec48423c08e56755613597463ec4222d8dffda11c5bc84760ad4221eca1e`. O manifesto linux/amd64 é `sha256:989543f86b2f18a74c921d5a54154a67853e04087046f25bf16101c6e3e15677`. O Finance permanece em actionfinance-web:27. O retorno da aplicação é isa-web:13, versão 0.6.4.

A migração 5 já está aplicada na base publicada e só acrescenta colunas e a preferência de conta. Nesta sessão não houve uma cópia nova imediatamente antes da subida. A rotina de cópia já existente inclui a preferência, porque o despejo lógico lista as tabelas do titular, e as colunas novas acompanham a tabela `account`.

## Limite

Não houve sessão autenticada na conta publicada. Isto não é aceite do proprietário. A aplicação 0.6.4 ainda abre a base, porque a migração só acrescenta colunas, mas não distingue uma quantia em dólar de uma quantia em reais. O retorno seguro da apresentação é a 0.6.5. Sem `end_session_endpoint` no diretório, sair não apaga sozinho a sessão do provedor.
