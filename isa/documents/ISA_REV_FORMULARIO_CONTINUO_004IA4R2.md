# ISA 0.6.8 — Cadastro contínuo de contas e hierarquia de títulos

26/10/2026. Revisão 004IA4R2. A apresentação recolhida de 004IA4 e 004IA4R1 deixa de valer para o formulário de conta.

## O que a pessoa vê

A página diz **Adicionar conta** ou **Editar conta**, com uma frase e o retorno às contas. Dentro do cartão, **Dados da conta** fica aberto. A ordem é banco, número e tipo, moeda, código e nome da agência, **Contatos do Banco**, e as ações **Salvar conta** e **Cancelar**.

O banco é uma busca. O resultado aparece como `001 — Banco do Brasil`. A escolha grava instituição e código juntos. Texto livre não cadastra banco. A moeda fica visível, com **BRL — Real** no cadastro novo. Se a conta já tem movimentação, a moeda aparece e a edição fica indisponível.

Agência e contatos continuam opcionais. O número aceita `0012345-6`. O código da agência aceita `0123-4`. Não há campo Dígito no formulário. O dígito já gravado permanece na base e, na edição, aparece em **Já registrados nesta conta**, junto com apelido, país e e-mail da agência quando existirem.

A lista vazia tem uma frase e um único botão **Adicionar conta**. Com contas, o botão fica no cabeçalho e o convite de primeira conta some. Falha de carregamento não é apresentada como zero contas.

Os títulos da ISA usam a mesma escala: H1 28 px no desktop e 25 px no celular, H2 20 px e 19 px, H3 16 px. Rótulo de campo 14 px. Isso vale para Início, Lançamentos, Planejar, Contas e Perfil, sem mudar cálculo, filtro ou lote.

## Catálogo

A amostra local continua com dez instituições e códigos COMPE em texto, conferida em 26/10/2026. Não é a relação do Banco Central. Instituição sem código nacional não recebe um código inventado. Conta já gravada fora da amostra continua editável. A busca sem resultado diz que a lista pode ser ampliada.

## Schema 8

A coluna nova é `account.agency_name`. A migração só acrescenta. Apelido, país, dígito, e-mail da agência e contatos já gravados não são apagados quando o formulário não os envia. Código de banco e nome de instituição novos precisam concordar com o catálogo. A combinação adulterada é recusada. Nenhuma alteração cadastral cria saldo ou lançamento.

## Prova de laboratório

Base sintética isolada, sem a conta publicada. 14 testes SQLite de contas e lotes passaram, incluindo nome da agência, número `0012345-6`, código `0123-4`, preservação de dígito, apelido, país e e-mail da agência, recusa de banco incoerente e isolamento da outra pessoa.

No navegador de laboratório, em 1440, 1280, 768, 390 e 360 px: lista vazia com uma chamada, erro de rede sem convite de primeira conta, busca por Brasil, 1 e 001, escolha por teclado e clique, moeda visível, contatos abertos, conta salva e nome da agência relido. H1/H2/H3 medidos em 28/20/16 px no desktop e H1 25 px a 390 px. Capturas em `documents/reviews/contas-004ia4r2/`.

O Chromium headless desta sessão não aplicou zoom de navegador de 200%: a densidade ficou em 1 e a largura útil em 1280. O reflow foi conferido nas larguras reais acima, sem escala de CSS. Não houve sessão autenticada na conta publicada.

## Publicação

Antes desta revisão, https://isa.actionhub.com.br respondia `isa-piloto 0.6.7`, schema 7, autenticação oidc e banco postgres. Esta revisão prepara a `0.6.8` e o schema 8 no código. A imagem ainda não foi publicada nesta entrega: o host público continua na 0.6.7 até o backup, a imagem e a task do serviço `isa` existente. Não houve ALB novo nem alteração no Finance ou na Spider.

O retorno compatível da aplicação, quando a 0.6.8 estiver no ar, é `isa-web:16`, versão 0.6.7. Ela abre o schema 8 porque a migração só acrescenta a coluna, e continua lendo contas, lotes e lançamentos. Não apaga o nome da agência gravado pela versão nova; apenas não o apresenta.

## Aceite

A prova acima é de laboratório. Não é verificação autenticada no host público nem aceite do proprietário. Saúde 200 não substitui esse aceite.
