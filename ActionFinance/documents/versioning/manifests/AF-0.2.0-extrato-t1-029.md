# Manifesto — produto 0.2.0, extrato T1

Estado: **candidata** em 15/10/2026. Não publicada. O produto servido permanece 0.1.2.

| Campo | Conteúdo |
|---|---|
| Versão e estado | 0.2.0 candidata. Menor versão nova porque a observação de extrato é capacidade nova. Não substitui 0.1.2 no ar |
| Base | AF-BL-023 revisão 1.2. Prompts 029 a 033. Versionamento do Prompt 024 |
| Escopo | Receber o relatório de liquidação, preservar todas as ocorrências do lote, consolidar evento só quando a identidade distingue e mostrar o total parcial das linhas elegíveis. O CSV de laboratório permanece separado. Sem título, baixa, movimento, saldo, categoria ou iniciativa |
| Continua aberto | Prova autenticada do pagamento de R$ 90 e repetição idempotente do 027. Aceite visual. Vínculo produtivo da referência da conta. O que representa a segunda linha dos 9 pares. O checksum de V20 no RDS não é o checksum Flyway 11 do mesmo texto |
| Schema | V13 a V23 no repositório. Mínimo da candidata: V23. O RDS público permanece V20 |
| Código | Sem tag Git. Branch `feat/actionfinance-extrato-032`, commit de código `e160996f34f2d08bdc6ac29b8055a3b0e9167b64`. Versão 0.2.0 em `pom.xml`, `package.json` e `application.properties` |
| Spider, Hub e Mercado Pago | Não alterados. Nenhuma chamada nova |
| Anterior / rollback | `actionfinance-web:16` · `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` · SPA `index-B0699gCh.js` · produto 0.1.2. Voltar a imagem não desfaz schema nem dados |
| Artefato | `actionfinance:candidate-033`. Índice `sha256:fcce948d9ba074b75af0352d1bb5a29c9f27e240e2c341039312a80318089256`. Manifesto da plataforma `sha256:2e6ccb8fed8dd65f7b1547a1ef65cd8c0ff70b889454163b536f066183ecd31f`. JAR `sha256:c242c6c7e6cdf8749b082ceb764320e1cfeaa1972688ee8e99a17c49ebd34338`. SPA `index-DzYbnxZv.js`. Parser `1`. Perfis `mp-account-money-csv-1` e `mp-settlement-v2-csv-1` |
| Validação | Checkout limpo do commit de código. Ensaio isolado V20 → V23 e jornada sanitizada de 22 ocorrências. Não é carga produtiva |
| Relato | [REV_029](../../reviews/ACTIONFINANCE_REV_EXTRATO_T1_029.md) · [REV_030](../../reviews/ACTIONFINANCE_REV_ADEQUACAO_EXTRATO_030.md) · [REV_031](../../reviews/ACTIONFINANCE_REV_EXTRATO_REAL_031.md) · [REV_032](../../reviews/ACTIONFINANCE_REV_CONSOLIDACAO_EXTRATO_032.md) · [REV_033](../../reviews/ACTIONFINANCE_REV_BASE_REPRODUZIVEL_033.md) |
