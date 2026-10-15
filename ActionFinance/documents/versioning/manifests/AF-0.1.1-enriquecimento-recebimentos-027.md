# Manifesto — produto 0.1.1, enriquecimento de recebimentos

Estado: **publicado** em 15/10/2026. Aceite do proprietário: **não atribuído**. A sincronização autenticada desta versão ainda não foi executada.

| Campo | Conteúdo |
|---|---|
| Versão e estado | Produto 0.1.1. Patch distinto de 0.1.0 porque a lista, o merge e o texto da tentativa mudaram |
| Base | AF-BL-023 revisão 1.1. Prompt 027. Versionamento do Prompt 024 |
| Escopo | Transporte e apresentação dos dados de recebimento já existentes na origem. Sem movimentos, posição, conciliação, rateio ou iniciativa |
| Schema | Flyway V20 já aplicado. Nenhuma migration nova. Checksum V20 `-145522935` |
| Finance | `actionfinance-web:15` · `sha256:61cf094d2673d2344c293612b484e2c16cdb2d7cdc1458eebdab17a936e628cc` · SPA `index-UhuYx_ma.js` · JAR `fb974dfd5621383890d67bacd00deb728e9742f0c5517bd4a5d19dbac031307e` |
| Spider | Somente runtime `spider-runtime-prod:4` · `sha256:d116496379aff3c341682908f2ac7fef5ac06dd46ab59fbf332a2c22cad8bec0`. Query e projector permanecem na revisão 3 |
| Hub | `services/gateway-api/domain/spider-pay-lookup.js` no gateway `3.17.19.188`. Banco efetivo `paneldx-database` / `leaction_hub` |
| Resposta | Revisão de item 2026-10-15, aditiva. Requisições 1.3 e 1.4 preservadas. 1.5 não reutilizada |
| Anterior | `actionfinance-web:14` · `sha256:cb0619f2f1b4b38c86da43298cc11cd1979dbe25dc4dc5f25c1f6533072c528a` · Spider `sha256:ca0cdfdd0494499759c2f059c883e73039453df8e19d3e1ba0c073fe95bd9430` |
| Validação | Testes de merge, integração, página, adapter e lookup. `system/info` público `version=0.1.1`. Prova autenticada: **não** |
| Relato | [REV_027](../../reviews/ACTIONFINANCE_REV_ENRIQUECIMENTO_RECEBIMENTOS_027.md) |
