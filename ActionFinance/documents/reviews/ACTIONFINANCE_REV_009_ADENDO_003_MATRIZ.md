# Matriz Hub × Mercado Pago — PRM_009 ADENDO_003

Data da leitura: 02/10/2026. `apply=false`. Identidades só por sufixo. Sem e-mails nem IDs completos de pagamento.

Consulta autenticada ao provedor. GET de pedido PAID **pode** actualizar observação depois desta leitura; um APPLY futuro tem de reler `updated_at` / `provider_observed_at` e não sobrescrever revisão posterior.

Conta de destino observada: sufixo do `collector_id` **2340** nas oito linhas com referência. Linha sem referência: destino ausente.

| Sufixo | Método | Cobrado (cêntimos) | Observado MP | Pago proposto | Confirmado | Hub | MP | live_mode | Divergência | Proposta |
|---|---|---:|---:|---:|---|---|---|---|---|---|
| e8c19cfd | pix | 100 | 100 | 100 | sim | PAID | approved | true | nenhuma | gravar pago confirmado + `pix.status=approved`; sem fulfill/outbox |
| 039db4bf | pix | 7000 | 7000 | — | não | PENDING | cancelled | true | **hub=PENDING mp=cancelled** | observado sem pago; manter PENDING; não usar `transaction_amount` como pago |
| 36de07eb | pix | 7000 | 7000 | 7000 | sim | PAID | approved | true | nenhuma | pago confirmado; sem fulfill/outbox |
| 4835a12f | pix | 7000 | 7000 | 7000 | sim | PAID | approved | true | nenhuma | pago confirmado; sem fulfill/outbox |
| 524ef941 | pix | 7000 | 7000 | 7000 | sim | PAID | approved | true | nenhuma | pago confirmado; sem fulfill/outbox |
| d59ef70b | pix | 7000 | 7000 | — | não | CANCELLED | cancelled | true | nenhuma | observado sem pago; manter CANCELLED |
| 7b82585a | card | 7000 | — | — | não | PAID | sem referência | — | **hub=PAID mp=pendente** | linha permanece pendente; não inventar pago |
| 7c3efeb3 | pix | 7000 | 7000 | 7000 | sim | PAID | approved | true | nenhuma | pago confirmado; sem fulfill/outbox |
| c2dbef84 | pix | 7000 | 7000 | 7000 | sim | PAID | approved | true | nenhuma | pago confirmado; sem fulfill/outbox |

Resumo: 6 alinhados PAID/approved com pago proposto; 1 CANCELLED alinhado sem pago; 1 PENDING vs cancelled (divergência explícita); 1 PAID cartão sem referência (pendente). `updated_at` presente nas nove. Preço comercial R$ 70 **não** usado. APPLY histórico **parado**.

Artefacto restrito no servidor: `/var/www/leaction-platform/.dev-logs/prm009-adendo003-history-dryrun.json` (0600).
