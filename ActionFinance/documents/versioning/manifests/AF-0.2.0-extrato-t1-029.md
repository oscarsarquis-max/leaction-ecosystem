# Manifesto — produto 0.2.0, extrato T1

Estado: **candidata** em 15/10/2026. Não publicada. O produto servido permanece 0.1.2.

| Campo | Conteúdo |
|---|---|
| Versão e estado | 0.2.0 candidata. Menor versão nova porque a observação de extrato é capacidade nova. Não substitui 0.1.2 no ar |
| Base | AF-BL-023 revisão 1.2. Prompts 029, 030 e 031. Versionamento do Prompt 024 |
| Escopo | Receber o relatório de liquidação no perfil `mp-settlement-v2-csv-1`, pré-visualizar, confirmar só as linhas elegíveis e consultar a observação. O CSV de laboratório permanece separado. Sem título, baixa, movimento, saldo, categoria ou iniciativa |
| Continua aberto | Prova autenticada do pagamento de R$ 90 e repetição idempotente do 027. Aceite visual. Vínculo produtivo da referência da conta. Identidade dos 9 pares repetidos do relatório real |
| Schema | V21 e V22 no repositório. O RDS público permanece V20 |
| Código | Sem tag Git. Versão 0.2.0 em `pom.xml`, `package.json`, `application.properties` e no nome do jar do script de imagem. A imagem de produção não foi construída |
| Spider, Hub e Mercado Pago | Não alterados. Nenhuma chamada nova |
| Anterior / rollback | `actionfinance-web:16` · `sha256:bcf11a54e4017cd5d4e64efce860ee1e47cfc716f77698980f8c3c33fbb34dec` · SPA `index-B0699gCh.js` · produto 0.1.2. Voltar a imagem não desfaz schema nem dados |
| Validação | Parser do arquivo real, só em memória. Jornada de tela com fixture sanitizada, capturas em `screenshots/extrato-031/`. A jornada não é a carga produtiva |
| Relato | [REV_029](../../reviews/ACTIONFINANCE_REV_EXTRATO_T1_029.md) · [REV_030](../../reviews/ACTIONFINANCE_REV_ADEQUACAO_EXTRATO_030.md) · [REV_031](../../reviews/ACTIONFINANCE_REV_EXTRATO_REAL_031.md) |
