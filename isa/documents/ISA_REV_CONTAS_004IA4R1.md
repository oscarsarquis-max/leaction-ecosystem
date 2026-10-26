# ISA 0.6.6 — Experiência de contas

19/10/2026. Revisão da 0.6.5 depois da prancha aprovada. O schema passa a 6. A base, as identidades e o serviço continuam os mesmos.

A apresentação recolhida desta revisão foi substituída em 26/10/2026 pela 0.6.8. O cadastro de conta fica aberto, sem Mais informações e sem o link Alterar para revelar a moeda. A hierarquia de títulos vale para a ISA inteira. Ver `ISA_REV_FORMULARIO_CONTINUO_004IA4R2.md`.

## O que a pessoa vê

O cabeçalho tem a marca, o seletor **Visualizando**, o nome de apresentação e **Sair**. A gestão fica só no destino **Contas**. Sem nome gravado, o cabeçalho oferece **Seu perfil**. No Perfil, a pessoa salva como quer aparecer. A identidade de acesso mostrada é o e-mail verificado quando o diretório o envia; hoje o pedido de entrada pede só o escopo `openid`, e esse token não traz nome. A ISA não inventa o nome a partir do e-mail.

A lista se chama **Suas contas**. Criar uma conta pede banco, número e tipo. Apelido, país, código, agência, dígito, contatos e liquidez ficam recolhidos e são opcionais. A moeda inicial é BRL · Real, com ação para alterar. O número guarda zeros à esquerda. Sem apelido, o rótulo usa o banco e o número mascarado. A lista não mostra o número completo.

O detalhe separa **Acesso e importação** de **Dados e contatos**. Importar extrato abre a jornada com a conta escolhida.

## Acesso automático

Não há conector bancário no código, na task da ISA nem um contrato de Open Finance habilitado para esta conta. A tela diz isso e oferece o arquivo compatível. Não existe botão que finja conexão. A prioridade, quando houver autorização, é o Banco do Brasil da própria pessoa, só para consulta, sem senha digitada na ISA.

Para habilitar de verdade falta um fornecedor regulado ou o próprio banco, com contrato, escopos e destino dos dados. Nenhum preço foi encontrado na infraestrutura autorizada, e nenhum serviço foi contratado nesta entrega.

## Persistência

A migration 6 acrescenta número, agência, código, país, apelido, e-mails do banco e as tabelas de contato e de nome de apresentação. Contas antigas continuam consultáveis sem esses campos. A moeda não muda depois de haver movimentação. Repetir o envio com o mesmo identificador não cria outra conta. Contatos não entram na leitura da IA. Outra pessoa não lê a conta nem o nome.

Antes desta subida, a task existente `isa-backup:5` concluiu com saída 0 e enviou a cópia `backups/20261019T175327+0000/`, com 22 tabelas. Essa cópia é do schema anterior à migration 6. A cópia lógica e a exclusão por titular, na aplicação nova, incluem os campos novos. O retorno 0.6.5 ainda abre a base e continua distinguindo as moedas, mas não mostra número, contatos nem o nome de apresentação. O retorno 0.6.4 continua apresentando dólar como real; não é um retorno seguro da apresentação. A apresentação desta entrega é a 0.6.6.

## Prova de laboratório

48 testes em SQLite temporário, incluindo os três campos obrigatórios, o zero à esquerda, a repetição sem duplicar, o contato isolado e o nome que não passa para outra pessoa. O mesmo cenário de migração e isolamento rodou no PostgreSQL local `127.0.0.1:5442`, com base descartável, e chegou ao schema 6. Não é a conta publicada.

No navegador de laboratório, em 1440, 1280, 768, 390 e 360 px: nome salvo, saída, outra pessoa sem esse nome, cadastro só com banco, número e tipo, erro no campo, e-mail inválido, lista sem o número completo, abas e ausência de botão de conexão. Capturas em `documents/reviews/contas-004ia4r1/`. Não houve prova autenticada na conta publicada nem zoom de 200% nesta rodada.

## Publicação

Servida em https://isa.actionhub.com.br como isa-piloto 0.6.6, task isa-web:15, no serviço isa já existente. Saúde 200, base postgres, Claude no Bedrock. `/api/ready` responde schema 6. `/api/workspace` sem sessão responde 401. O `app.js` servido traz **Visualizando** e **Sair**, e não traz “Gerenciar contas”.

A imagem registrada é o índice `sha256:373dcbee4441a7fa3380f7cb5b0f10a9b67cfc6e3a02a9ce22c136c075a9bad6`. O manifesto linux/amd64 é `sha256:7b76c9037d411d34f8c3946a272c3faa6cf67175263c8b55334f201307e83c52`. O Finance permanece em actionfinance-web:27. O retorno da aplicação é isa-web:14, versão 0.6.5. Essa versão distingue as moedas e abre o schema 6, porque a migração só acrescenta colunas e tabelas; ela não apresenta número da conta, contatos nem o nome de apresentação.

Não houve sessão autenticada na conta publicada. Isto não é aceite do proprietário. O zoom real de 200% não foi repetido nesta rodada.
