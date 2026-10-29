# Prompt 63 — Somente entrega; calendário do Criador

Novos pedidos são entrega. Não há retirada comercial. Frete ficou de fora.

## Causa do calendário do Criador

O passo 4 usava um calendário local (dias do mês + data mínima). A home usa `BakeCalendar` + `POST /api/v1/schedule/preview`. Sem marcadores de fornada. O Criador passou a reutilizar o mesmo componente e a mesma agenda, enviando a composição real (`custom` + farinha/preparo/quantidade).

Igualdade = mesmos dias de produção. Os rótulos podem diferir: a home sem carrinho diz «dia de produção aberto»; o Criador com ficha válida diz «cabe nesta seleção; a confirmação depende do aceite».

## Isolado

- Pedido padrão com endereço → `delivery`, total intacto, idempotência.
- Payload `fulfillment_modality=pickup` → 422 acionável.
- Pedido histórico de retirada sem endereço continua operável; endereço não converte a modalidade.
- Solicitação avulsa de data sem endereço.
- Home e passo 4: mesmos 9 dias de outubro (qua/sáb).
- Quantidade com área de toque ≥ 44 px.
- Gigio no celular não cobre a nota do passo 4.
- Pergunta «Vocês fazem retirada?» → somente entregas; sem e-mail pessoal.

Pedido isolado de prova: `LP6836B74B06` (não é produção).

## Produção

Navegação e validação sem envio. Imagem `lojadepaes:prod-20261001i`, bundle `/assets/index-DECrXnns.js`. Rollback `prod-20261001h`. Alembic `c8e2f1a90b64` inalterado. Sem migrate, seed, cobrança ou e-mail real de teste.

Home e passo 4 do Criador (composição farinha branca + massa maturada + pão de forma) mostram os mesmos 8 dias de outubro (domingo/quarta). Os rótulos diferem de forma legítima: a home diz «dia de produção aberto»; o Criador diz «cabe nesta seleção; a confirmação depende do aceite». A agenda real não foi alterada para a prova.

Checkout em 320/390/768/1440: só entrega, endereço obrigatório, «Horário preferido para entrega», sem convite à retirada. Gigio não cobre a nota do passo 4 em 320/390/768.

Pergunta «Vocês fazem retirada?»: A Loja trabalha apenas com entregas; sem e-mail pessoal e sem política de frete inventada.

`POST /api/v1/storefront/orders` com `fulfillment_modality=pickup` → 422. Endereço ausente → 422. Nenhuma referência criada.
