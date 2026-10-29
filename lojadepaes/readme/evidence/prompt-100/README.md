# Prompt 100 — Aceite com quantidade já informada (21/10/2026)

Leitura de produção e cenário isolado são coisas diferentes. O healthcheck não prova o aceite. Nenhum aceite, e-mail ou cobrança foi feito na solicitação real.

## Causa

A solicitação `SD3CC4C139` (UUID com prefixo `3cc4c139`) está pendente, recebida em 20/10/2026, data desejada 23/10/2026, `intended_quantity` 1, `cart_context` vazio e mensagem preenchida. Não há pedido vinculado nem complemento de endereço.

A prévia e a conversão só liam linhas com `variant_id` no `cart_context`. Com o carrinho vazio, ignoravam a quantidade já gravada e o texto, e respondiam “faltam os pães e as quantidades da encomenda”. O pão estava no catálogo publicado, com uma opção de preço, e o nome aparece na mensagem.

## O que a correção faz

- Quantidade persistida (≥ 1) reaparece na prévia. Não é trocada por um padrão.
- Seleção estruturada continua valendo e aceita direto.
- Pão só na mensagem: o administrador escolhe o produto real na área de aceite. Correspondência única de nome e de opção é sugerida. Texto livre ou mais de um nome/opção não vira SKU sozinho.
- Vários pães exigem quantidade explícita em cada um, somando a quantidade informada.
- Prévia mostra produto, quantidade, preço vigente e total. Sem preço vigente, não há total nem pedido.
- Aceite cria um pedido, reserva pela regra já existente e enfileira o aviso de aceite com logo, resumo, valor, link protegido de pagamento e pendências de endereço e telefone.
- Endereço e telefone não bloqueiam aceite nem pagamento.
- Fechamento explícito da Agenda, data passada, capacidade e preço continuam rejeitando.
- Clique repetido e aviso com falha de envio devolvem o mesmo pedido e o mesmo evento de e-mail.
- A solicitação real não foi aceita, reprocessada nem apagada.

## Cenário isolado

`tests/test_prompt100.py`: 8 testes, dados fictícios. Cobre mensagem com quantidade 1, seleção estruturada, mensagem ambígua, várias opções do mesmo nome, preço ausente, fechamento, capacidade e data excepcional sem endereço. A suíte de regressão de solicitação (`test_prompt87_date_request`, `test_prompt68`, `test_prompt96b`) passou no mesmo comportamento. Interface: `AdminApp.test.tsx` mostra a pendência correta, o total depois da confirmação do pão e o aceite enviando a linha escolhida.

## Leitura de produção, sem efeito

Depois da imagem nova, a prévia só de leitura (transação desfeita) desta solicitação:

| Campo | Valor |
|---|---|
| Estado | `pending`, sem pedido, antes e depois da leitura |
| Quantidade | 1 |
| Aceite sem escolha | não |
| Lacuna | a quantidade 1 está informada; confirmar o produto do catálogo |
| Sugestão | Rolled Bread de Pepperoni com Muçarela e Manteiga de Alho · 500 g · R$ 70,00 |
| Prévia com essa opção | aceite possível, total R$ 70,00, sem outra lacuna |
| Pendências | endereço de entrega, telefone |
| Pacote publicado | `index-DE4l_sbu.js` contém o texto de confirmar o pão |

O proprietário revisa esse total e clica em Aceitar. Esta entrega não fez isso.

## Publicação

| Item | Valor |
|---|---|
| Imagem | `lojadepaes:prod-20261021a` |
| Rollback de app | `lojadepaes:prod-20261011a` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261021T115706Z.sql.gz` (96471 bytes) |
| Alembic | `d7e0f5a24b38` (head, sem migração nova) |
| Saúde | `{"status":"ok","service":"lojadepaes"}` — não prova o aceite |

Rollback: recolocar `LOJADEPAES_API_IMAGE=lojadepaes:prod-20261011a` e recriar o serviço `api`. O backup restaura o banco se for preciso; esta correção não alterou schema nem a solicitação.
