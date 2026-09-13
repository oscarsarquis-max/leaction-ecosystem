# SEGSENSE_MOCK_CONTRACT_001 — Contrato do Insurance Provider Mock

Cópia de rastreio na aplicação mock. O documento canônico permanece em `segsense/documents/SEGSENSE_MOCK_CONTRACT_001.md`.

Runtime independente na raiz do monorepo. Porta 8095, bind **127.0.0.1**. Sem default de credencial: o processo não inicia sem `SEGSENSE_MOCK_CREDENTIAL`. Apenas a Spider chama este processo. `origin=ILLUSTRATIVE_NOT_ICATU_CONTRACT`. **Não** é “Provider Satellite” certificado. Não é sandbox Icatu. Sem banco; fixture imutável no código. `originSnapshot` **não** atravessa esta fronteira.
