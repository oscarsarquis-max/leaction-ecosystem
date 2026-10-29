# Manifesto — schema V20 no produto 0.1.0

Estado: **schema publicado**. Produto **não** promovido. Não é aceite do proprietário.

| Campo | Conteúdo |
|---|---|
| Versão e estado | Produto 0.1.0 permanece publicado. Nenhuma candidata nova. Schema V20 aplicado em 15/10/2026 |
| Base | AF-BL-023 revisão 1.0. Este incidente não amplia o escopo financeiro da baseline |
| Escopo | Correção da leitura/gravação da sincronização de recebimentos. Tesouraria 023 **não** iniciada. 019/020/021 continuam abertas |
| Mudanças | Oito colunas anuláveis em `pay_receipt_transaction` e um check de `payer_kind`. Sem título, baixa, movimento ou saldo |
| Código | Imagem já publicada, sem rebuild. Task `actionfinance-web:14`. Digest `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a` |
| Artefatos | SPA no host: `index-CRjEQs1k.js`. `GET /api/v1/system/info` → `version=0.1.0`, `RECEIPT_SYNC` |
| Banco | Flyway 1–20. V20 script `V20__pay_receipt_commercial_identity.sql`, checksum `-145522935`, `success=true` |
| Validação | Ensaio com `ROLLBACK` (coluna ausente de novo) e em seguida `COMMIT`. Consulta que falhava passou a executar. Prova autenticada na interface: **não** |
| Operação | Spider não alterada. Rollback do schema está no REV_025. Serviço web não foi reiniciado |
| Decisões | Aplicação do schema: execução do Prompt 025. Aceite do proprietário: **não atribuído** |
