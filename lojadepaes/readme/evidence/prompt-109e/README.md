# Prompt 109E — compra na vitrine, data só para o que não se vende, defeitos herdados

Banco de captura (`lojadepaes_capture`, porta 5438), Hub simulado. Nenhum dado real.

## Compra na vitrine (item 1)

A compra funciona de ponta a ponta em 390 px e em 1440 px: vitrine → "Escolher meu pão" → "Adicionar ao carrinho" → "Ir ao carrinho para finalizar" → dia no calendário → dados e endereço → "Finalizar compra" → página do pedido com "Pagar com Pix" e "Pagar com cartão" (sem pagar). Sem rolagem lateral.

Defeito real achado no caminho: a gaveta do carrinho continuava aberta por cima do carrinho e depois do envio. Corrigido (`CartContext.setOpen`, `CartAddedNotice`).

Capturas: `compra-vitrine-390.png`, `compra-vitrine-1440.png`, `compra-carrinho-390.png`, `compra-carrinho-1440.png`, `compra-pagamento-390.png`, `compra-pagamento-1440.png`. Passo a passo: `compra-passos.txt`.

| Teste | Veredito | Ação |
|---|---|---|
| 50, 52, 59, 60, 62 (foto) | Tela mudou de propósito: prompt 99 (commit 24977d4e) pôs o cartão da receita em moldura 16:9 com `cover` e `object-position` do foco; a página de leitura segue `contain`. | Teste atualizado (cartão `cover`, 16:9, sem vão lateral; leitura `contain`). CSS intacto. 50 também esperava a ficha carregar antes de publicar (corrida do teste). |
| 53 | Desatualizado: 105A (24977d4e) — "Seu carrinho", "Finalizar compra", endereço obrigatório; conciliação só com `approved` e valor pago. | Teste atualizado. |
| 54 | Desatualizado (mesmos textos) e corrida na contagem. | Teste atualizado. |
| 65 | Título desatualizado; a parte do admin revelou defeito real: "Ver a loja" ignorava o aviso de alterações não salvas. | Corrigido `AdminApp.go`; teste atualizado. |
| 58, 63 | Desatualizados: "Adicionar ao carrinho". | Teste atualizado. |
| 96b | Datas do fechamento fixas em outubro, já encerrado. | Datas relativas a hoje. |

## Solicitar outra data (item 1b)

`formulario-data-vendavel-390.png` (aviso "Esta data está disponível. Finalize o pedido pelo carrinho." + "Ir para o carrinho", sem enviar) e `formulario-data-fechada-390.png` (só "Enviar solicitação"). Servidor: `create_date_request` recusa data vendável com 409 e a mesma mensagem, pela mesma avaliação do calendário (`evaluate_day`). Dia fechado, cheio ou sem produção segue aceito. Exceção do operador não mudou. Testes: `test_prompt109e.py` (6) e `DateRequestForm.test.tsx` (12).

## Defeitos herdados (item 2)

- `test_storefront::test_submit_keeps_order_when_hub_refuses`: o pedido não se perde (fica aceito/confirmado e a cliente paga depois). O teste esperava o erro gravado, o que o 107B (savepoint) deixou de fazer. Teste atualizado. A falha do Hub agora só vai ao log.
- `test_house_fidelity_ledger::test_eighth_order_second_credit_and_month_keeps_credits`: o segundo crédito é gerado no 8º pedido. A falha era data fixa no teste. Corrigido o teste.
- `test_prompt53` (2 testes, só relato): `test_accept_sends_payment_mail_and_opens_checkout_once` confere o e-mail de aceite (assunto "Seu pão foi aceito…") — obsoleto, o assunto hoje é "Pedido aceito — pague e acompanhe LP…". `test_authorized_ops_to_routes_without_promoting_skipped` confere o roteamento para operação sem promover e-mail ignorado — obsoleto, o falso `send_outbox_email` não aceita o argumento `html_body`. Nenhum é defeito. Não alterados.

## Testes 67 e 68 (item 3)

67: volta a conferir "Há 1 solicitação aguardando resposta." em `/admin/agenda`. 68: confere o texto atual "Dados de entrega incompletos: falta rua, número, bairro, cidade, estado, CEP."

## Fila (item 4)

`fila-filtros-960-antes.png` / `-depois.png`, `fila-filtros-aberto-390-antes.png` / `-depois.png`, `fila-medidas-*.json`. Em 960 px o grupo "Em andamento" cortava "Em produção" sem sinal; agora quebra em até duas linhas, como no celular (divisor lateral some quando quebra). Em 390 px o botão "Filtros" aberto agora fica escuro; antes ficava igual ao fechado.

## Outros

- Corrida ao criar a linha única de `schedule_settings` num banco novo (duas requisições juntas): agora usa savepoint. Só afeta banco vazio.
- `F821` em `schedule.py` (`intake_paused_message` sem import no resumo do calendário): import local adicionado.
- Falha sem relação, não tratada: `test_prompt109c::test_reschedule_by_status_moves_slot_and_keeps_payment` (dependia da data do dia).
