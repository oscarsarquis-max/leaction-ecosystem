# ISA — fechamento e publicação das contas

26/10/2026. Continua o relato `ISA_REV_FORMULARIO_CONTINUO_004IA4R2.md`. Aquela candidata ficou em código local, com a amostra de dez bancos, com o PostgreSQL de laboratório em timeout e sem imagem publicada. Esta entrega fecha essas três pendências. O zoom real de 200% continua sem comprovação.

## O que está no ar

https://isa.actionhub.com.br responde `isa-piloto 0.6.8`, autenticação oidc, base postgres. `/api/ready` responde schema 9. `/api/workspace` sem sessão responde 401. O serviço existente `isa` está na task `isa-web:17`, rollout COMPLETED, uma tarefa em execução. A imagem linux/amd64 é `sha256:208d1a603b3af7ef3c22d532ff1a152275863fba73245a8f003d1d982931307c`.

`/app.js` e `/styles.css` respondem `Cache-Control: no-store`. O `app.js` servido contém “Não encontramos esta instituição na lista” e não contém a frase da amostra de dez instituições. O CSS servido contém 28 px e 25 px.

O retorno da aplicação é `isa-web:16`, versão 0.6.7. Essa versão para a migração no schema 7. Com o banco já no schema 9, ela não recria colunas e não apaga nome de agência, ISPB nem pedido de catálogo; apenas não apresenta o catálogo novo nem o nome da agência. Não se restaura a cópia anterior por cima da base ativa para voltar a aplicação.

O ActionFinance permanece em `actionfinance-web:28`, rollout COMPLETED. Não houve ALB, identidade ou banco novos.

O caminho de uso é https://isa.actionhub.com.br/#contas . Banco, número e tipo bastam. A moeda nova começa em BRL — Real.

## Catálogo

Fonte primária: CSV dos participantes do STR, aberto em 26/10/2026.

https://www.bcb.gov.br/content/estabilidadefinanceira/str1/ParticipantesSTR.csv

A página de dados abertos que aponta esse arquivo é https://dadosabertos.bcb.gov.br/dataset/lista-de-participantes-do-str . O arquivo não traz data oficial de atualização. O Banco Central descreve a relação como atualizada diariamente. 26/10/2026 é a data em que esta cópia foi obtida, não a data oficial.

A cópia versionada está em `server/catalog/ParticipantesSTR.csv` e entra na imagem. A busca no formulário usa essa cópia. Digitar não consulta o Banco Central.

Contagem desta cópia: 471 linhas. 460 com número-código de três dígitos. 11 sem número-código de três dígitos, entre elas oito com `n/a` e três câmaras B3 cujo campo veio como `0`. 14 em liquidação, fora da escolha de conta nova e mantidas no arquivo. 457 instituições podem ser escolhidas em cadastro novo.

ISPB, número-código e “Participa da Compe” são colunas diferentes. O valor `n/a` ou `0` não vira código nacional. A apresentação sem número-código é “Sem número-código — nome oficial”, e o identificador gravado é o ISPB.

A busca usa o nome extenso, o nome reduzido e o código. Código exato vem primeiro. Não há alias inventado. “Nubank” não está escrito na fonte; a instituição do código 260 entra como o nome oficial “NU PAGAMENTOS - IP”.

Cobertura: participantes do STR no Brasil. Não é catálogo mundial, não é a lista de todos os tipos de instituição e não cria banco estrangeiro porque a conta está em dólar.

A rotina `scripts/dev/update-str-catalog.py` baixa o mesmo URL para um arquivo temporário e só substitui a cópia se o cabeçalho e pelo menos 400 linhas estiverem presentes. Falha de download ou arquivo curto mantém a cópia anterior.

Conta já gravada com nome antigo, inclusive “Nubank” ou “Banco da Família”, continua editável sem troca obrigatória. Par código/nome que não confere com o catálogo nem com o registro atual é recusado no servidor. Se a busca não achar a instituição, a mensagem é “Não encontramos esta instituição na lista” e o botão registra o pedido. O rascunho permanece. Isso não cria conta e não consulta o banco.

## Schema e PostgreSQL

O schema 8 acrescenta `agency_name`. O schema 9 acrescenta `bank_ispb` e a tabela `catalog_request`. Os dois sobem juntos quando a base está no schema 7. A produção estava no schema 7 antes desta publicação e passou ao schema 9 na abertura da 0.6.8. Não houve reset nem seed.

O timeout anterior era o container `isa-pg-004p1` parado em `127.0.0.1:5442`. Ele foi iniciado de novo. A senha desse container continua só do laboratório. A base publicada não foi usada nos testes.

Em PostgreSQL 17.11 isolado, no código desta versão, passaram:

- `test_accounts.PostgresAccountTests`, incluindo migração de uma conta do schema 7 para o 9, com o mesmo id e o mesmo dono, conta nova com código 077 fora da amostra antiga, agência `0123-4`, nome “Agência Centro” relido em conexão nova, atualização de outro campo sem apagar o nome da agência, e restauração lógica;
- `test_pg.PostgresPilotTest`, incluindo transação desfeita sem conta incompleta, importação repetida sem duplicar e restauração que esconde a pessoa esquecida.

No SQLite, `test_accounts.AccountTests` e `test_work` passaram no mesmo código, 15 testes. O sucesso do SQLite não substitui a execução do PostgreSQL acima.

## Títulos e telas

A hierarquia medida no laboratório, com a fonte da página, está em `documents/reviews/contas-004ia4r3/medidas.json`.

| Jornada | Largura | H1 | H2 |
|---|---|---|---|
| Início, lançamentos, lotes, registrar, conferir, importar, planejar, perfil, contas | 1280 | 28 px, peso 700 | 20 px, peso 700, quando a seção existe |
| As mesmas jornadas conferidas no celular | 390 | 25 px, peso 700 | 19 px, peso 700, quando a seção existe |
| Formulário de conta | 1440 | 28 px | 20 px |
| Formulário de conta | 768, 390 e 360 | 25 px | 19 px |

O H3 “Pessoa de contato” mediu 16 px e peso 600 no formulário. Páginas sem subseção não ganharam um H3 só para completar a escala. Registrar e conferir, no estado vazio do laboratório, têm H1 e não têm H2. O Início não foi redesenhado.

O ciclo criar, salvar, listar, abrir, editar e reler depois de recarregar passou na base isolada, com número `0012345-6`, agência `0123-4` e nome “Agência Centro”. Não houve rolagem horizontal indevida nessas larguras.

## Zoom

O Chrome com janela, abertura em 1280×900, recebeu Control+Equal quatro vezes. `innerWidth` permaneceu 1280, `devicePixelRatio` permaneceu 1 e `visualViewport.scale` permaneceu 1. O zoom de página de 200% não foi aplicado e não está aprovado. A verificação manual ainda necessária é abrir https://isa.actionhub.com.br/#contas no Chrome, usar o zoom do menu em 200% e conferir se o formulário, o menu e os títulos refluem sem corte.

## Cópia e outros produtos

Antes da migration, a task `isa-backup:6` — imagem da 0.6.7, que já conhece lotes e contatos — gravou `backups/20261026T141153+0000/` no bucket privado `isa-pilot-253137917703`. Saída 0. 30 tabelas e 15 linhas, incluindo conta, contato e lote de trabalho. O conteúdo não entra neste relato.

Uma execução anterior, a task `isa-backup:5`, saiu 0 mas só copiou 22 tabelas, porque a imagem dela é anterior aos lotes. Essa cópia não é a referência de recuperação desta publicação. A agenda `isa-backup-daily` foi apontada para `isa-backup:7`, que usa a imagem 0.6.8, para as próximas cópias incluírem as tabelas novas. Uma execução dessa task, depois da migration, gravou `backups/20261026T141755+0000/`, saída 0, 31 tabelas, incluindo lote e pedido de catálogo.

## O que ainda falta

Não havia sessão autenticada disponível. A prova pública autenticada — abrir o formulário, ver o catálogo e ler as contas reais sem gravar dados sintéticos — fica pendente para o proprietário. Saúde 200 não substitui essa leitura.

O zoom de 200% fica pendente, como acima.

A cobertura estrangeira não foi feita. A fonte verificada nesta entrega é o STR brasileiro.

O 004IA6, reformulação do Início e do desempenho, não entrou nesta publicação.
