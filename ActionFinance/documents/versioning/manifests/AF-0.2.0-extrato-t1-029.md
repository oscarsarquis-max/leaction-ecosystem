# Manifesto — produto 0.2.0, extrato T1

Estado: **candidata** em 15/10/2026. Não publicada. O produto servido permanece 0.1.2.

| Campo | Conteúdo |
|---|---|
| Versão e estado | 0.2.0 candidata. Menor versão nova porque a observação de extrato é capacidade nova. Não substitui 0.1.2 no ar |
| Base | AF-BL-023 revisão 1.2. Prompts 029, 030, 031 e 032. Versionamento do Prompt 024 |
| Escopo | Receber o relatório de liquidação, preservar todas as ocorrências do lote, consolidar evento só quando a identidade distingue e mostrar o total parcial das linhas elegíveis. O CSV de laboratório permanece separado. Sem título, baixa, movimento, saldo, categoria ou iniciativa |
| Continua aberto | Prova autenticada do pagamento de R$ 90 e repetição idempotente do 027. Aceite visual. Vínculo produtivo da referência da conta. O que representa a segunda linha dos 9 pares. Versionar V13–V20, já aplicadas no origin e ainda fora do Git |
| Schema | V21, V22 e V23 no repositório deste incremento. O RDS público permanece V20 |
| Código | Sem tag Git. Versão 0.2.0 em `pom.xml`, `package.json`, `application.properties` e no nome do jar do script de imagem. A imagem de produção não foi construída |
| Spider, Hub e Mercado Pago | Não alterados. Nenhuma chamada nova |
| Anterior / rollback | `actionfinance-web:16` · `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` · SPA `index-B0699gCh.js` · produto 0.1.2. Voltar a imagem não desfaz schema nem dados |
| Validação | Parser do arquivo real, só em memória. Jornada sanitizada de 22 ocorrências em `screenshots/extrato-032/`. Não é carga produtiva |
| Relato | [REV_029](../../reviews/ACTIONFINANCE_REV_EXTRATO_T1_029.md) · [REV_030](../../reviews/ACTIONFINANCE_REV_ADEQUACAO_EXTRATO_030.md) · [REV_031](../../reviews/ACTIONFINANCE_REV_EXTRATO_REAL_031.md) · [REV_032](../../reviews/ACTIONFINANCE_REV_CONSOLIDACAO_EXTRATO_032.md) |
