# SEGSENSE_MOCK_CONTRACT_001 — Contrato do Insurance Provider Mock

Cópia de rastreio na aplicação mock. O documento canônico permanece em `segsense/documents/SEGSENSE_MOCK_CONTRACT_001.md`.

Runtime independente na raiz do monorepo. Porta 8095 (isolada `:19095`), bind **127.0.0.1**. Sem default de credencial: o processo não inicia sem `SEGSENSE_MOCK_CREDENTIAL`. Apenas a Spider chama este processo. Provider 1.0 ilustrativo (`ILLUSTRATIVE_NOT_ICATU_CONTRACT`), caminhos agrícolas demonstrativos `DISCOVER_SYNTHETIC_CROP_PROTECTION_PATHS` **sem R$**, e Provider 1.1 cotação sintética (`NON_BINDING_DEMO`, `GENERATE_SYNTHETIC_HOME_QUOTE`). **Não** é “Provider Satellite” certificado. Não é sandbox Icatu. Sem banco; regras no código. `originSnapshot` **não** atravessa esta fronteira.
