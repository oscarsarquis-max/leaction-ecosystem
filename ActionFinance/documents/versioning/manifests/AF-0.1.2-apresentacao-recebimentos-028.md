# Manifesto — produto 0.1.2, apresentação dos recebimentos

Estado: **publicado** em 15/10/2026. Aceite visual do proprietário: **não atribuído**.

| Campo | Conteúdo |
|---|---|
| Versão e estado | Produto 0.1.2. Patch distinto de 0.1.1 porque a apresentação da lista, dos filtros, do resumo e do detalhe mudou. A sincronização não mudou |
| Base | AF-BL-023 revisão 1.1. Prompt 028. Versionamento do Prompt 024 |
| Escopo | Composição e rótulos dos recebimentos já gravados. Sem movimentos, posição, conciliação, rateio ou iniciativa |
| Continua aberto | Detalhe autenticado do pagamento de R$ 90 e repetição idempotente do 027. Zoom real de 200% numa janela larga. Separação, no contrato do Hub, entre o e-mail do pedido e a chave interna `@amount.hub.local` |
| Schema | Flyway V20 já aplicado. Nenhuma migration nova. Leitura posterior à imagem: versão instalada 20 |
| Finance | `actionfinance-web:16` · `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` · SPA `index-B0699gCh.js` · CSS `index-BBnoBM7d.css` |
| Código | Sem tag Git. A imagem leva a versão 0.1.2 em `system/info` |
| Spider e Hub | Não republicados. Runtime, query, projector e lookup permanecem os do 027 |
| Anterior / rollback | `actionfinance-web:15` · `sha256:61cf094d2673d2344c293612b484e2c16cdb2d7cdc1458eebdab17a936e628cc` · SPA `index-UhuYx_ma.js` |
| Validação | Sete testes da página. Capturas de viewport em 360, 768, 1280 e 1848 px. `system/info` público `version=0.1.2`. Contadores e md5 dos recebimentos iguais antes e depois |
| Relato | [REV_028](../../reviews/ACTIONFINANCE_REV_APRESENTACAO_RECEBIMENTOS_028.md) |
