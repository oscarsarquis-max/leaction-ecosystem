# Manifesto — produto 0.2.3, desbloqueio da importação

Estado: **publicada** em 15/10/2026. A carga produtiva do extrato não foi feita. A conta já cadastrada pelo operador não foi alterada.

| Campo | Conteúdo |
|---|---|
| Versão e estado | 0.2.3 publicada. Correção da leitura do relatório e do saldo desconhecido sobre 0.2.2 |
| Base | AF-BL-023 revisão 1.2. Prompt 043 |
| Escopo | Ordem da importação e representação de saldo ausente. Sem parser novo, sem schema, sem Spider, Hub, Mercado Pago ou Cognito |
| Continua aberto | Aceite do proprietário. Prova autenticada do host público. Importação do relatório real |
| Schema | V23, sem migration neste ciclo |
| Código da imagem | Sem tag Git. Branch `feat/actionfinance-extrato-032`, commit `8a57ce44c6779c55a63eff9ed9d87065d0fe19c7` |
| Anterior / rollback | `actionfinance-web:19` · `sha256:98942e11efae9774fb5df8244fb830a26fa10a1ec968dc1b56c3fded07b69611` · SPA `index-CbYwmC0n.js` · produto 0.2.2 |
| Artefato | `actionfinance-web:20`. Tag `0.2.3`. Índice `sha256:84565d8b0257de55ee8c0b0cd879110d33ff196c609afafcb6b056c476244580`. Manifesto da plataforma `sha256:1ade891cb053d3314601516ba97a50d036221559a5f90c493c6bdd4ec70fca1a`. JAR `sha256:fca4a4ce5dfdd80e9a30169d1018d44b300be2d6752c031b0e0e1d4bf8da2c5d`. SPA `index-Dlf7Kh7L.js` |
| Validação | Testes de interface e `StatementObservationIT`. Clique isolado da identificação e do saldo não apurado. Health do host conferido após o rollout |
| Relato | [REV_043](../../reviews/ACTIONFINANCE_REV_DESBLOQUEIO_IMPORTACAO_043.md) |
