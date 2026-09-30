# Prompt 53 — evidência isolada

Jornada Playwright em `:5084` com API/banco de teste e SES/Hub só nas fronteiras. Não é produção. Nenhum e-mail real saiu.

| Arquivo | O que mostra |
|---|---|
| `identify-1440.png` / `390` / `320` | Fechamento com nome e e-mail; envio sem nome bloqueado; escolhas e R$ 70,00 preservados |
| `confirm-1440.png` / `390` / `320` | Pedido persistido, “Aguardando avaliação da padaria”, Ver meu pedido, Voltar à loja |
| `admin-1440.png` / `390` / `320` | Nova solicitação, composição completa, aviso admin skipped (destinatário operacional vazio) |
| `accepted-1440.png` / `390` / `320` | Após aceite: data reservada, Pix e cartão disponíveis, ainda não pago |
| `payment-1440.png` / `390` / `320` | Pix simulado (código capturado, sem provedor real) |
| `paid-1440.png` / `390` / `320` | Conciliação autenticada: Pagamento: Pago |

Recarga da confirmação não reenviou o pedido. Segundo aceite não duplicou reserva. Aviso administrativo permanece skipped até existir `MAIL_OPS_TO` entregável.

Produção publicada: `lojadepaes:prod-20260929j`, bundle `/assets/index-E0LS4EAN.js`. Rollback de app: `prod-20260929i`.

| Arquivo | Site publicado |
|---|---|
| `prod-identify-1440.png` / `390` / `320` | Fechamento real até antes do envio: validação de nome, sem pedido criado |
