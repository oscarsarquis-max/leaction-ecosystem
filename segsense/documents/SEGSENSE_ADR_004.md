# SEGSENSE_ADR_004 — Autorização e fronteira do MVP integrado de demonstração

## Controle

- Projeto: SegSense
- Categoria: decisão arquitetural
- Versão: 1.0
- Data: 13/09/2026
- Estado: decisão do patrocinador para orientar `SEGSENSE_PRM_013`; execução ainda não iniciada

## Decisão

O patrocinador autorizou que o próximo prompt coordene **alterações mínimas também no repositório Spider** para uma demonstração integrada, desde que SegSense, Spider e Insurance Provider Mock permaneçam aplicações independentes. A autorização não é licença para refatorar a Spider, incorporar SegSense ou mock nela, alterar seu fluxo bancário ou declarar o Satellite Contract completo como implementado.

O identificador de **todo documento, decisão, contrato de demonstração, fixture, cenário e artefato novo originado deste trabalho** começará por `SEGSENSE_`. Onde convenções técnicas não admitirem esse prefixo literal (por exemplo path HTTP, package Java ou nome de migration), o nome funcional e o registro documental manterão rastreabilidade inequívoca ao identificador `SEGSENSE_*`. Arquivos preexistentes da Spider preservam seus nomes e histórico; não renomeá-los artificialmente.

## Fronteira do MVP

`SegSense → Spider → Insurance Provider Mock → Spider → SegSense` deve ser uma cadeia de chamadas **reais em ambiente local de demonstração**, com correlação e resultado verificáveis. O mock terá processo, configuração, porta e armazenamento/fixtures próprios, fora das árvores `spider/` e `segsense/`. A Spider é dona do recebimento do objetivo e contexto, da decisão governada e do acionamento do mock. SegSense é dono da experiência, da origem contextual, da manifestação e da apresentação do resultado. O mock é provedor fictício, não sistema nem sandbox da Icatu.

O produto apresentado será uma **pré-proposta demonstrativa não vinculante**, com dados sintéticos, premissas, data/versão, rastreabilidade da decisão e limites explícitos. Não é proposta de contratação, cotação oficial, garantia de elegibilidade, cobertura vigente ou apólice. Qualquer número ilustrativo será marcado `SINTÉTICO / NÃO COMERCIAL` em tela e documento. Preferir ausência de prêmio/capital a valores que possam ser confundidos com oferta real. Não usar nome, logo, código, condição ou produto da Icatu como se fosse origem da simulação. A reunião com Icatu e corretora é descoberta comercial, não aprovação presumida.

## Addendum SPIDER-SAT-003 (13/09/2026)

O Satellite Contract V1 passou a existir **na Spider** (`SPIDER-SAT-003`). SegSense é o primeiro EXPERIENCE SATELLITE e consome `POST /v1/satellites/interactions`. Isto **não** torna o contrato uma API do SegSense. O mock permanece TEST DOUBLE. Icatu permanece NOT_IMPLEMENTED. Esta ADR continua a impedir Data Plane, CAP-021 e CTX-004.

## Contratos e segurança

Criar contrato de demonstração **mínimo, versionado e documentado** (`SEGSENSE_DEMO_CONTRACT_001`), sem alegar certificação SAT-01–SAT-10 ou Satellite Contract pleno. Separar identidade do satélite, usuário e canal. Restrição a profiles locais de demonstração, autenticação serviço-a-serviço baseada em mecanismo existente ou segredo de ambiente não versionado, allowlist de origens/destinos, idempotência, correlação, timeout e falha fechada. Sem PII real; fixture sintética. Nunca vazar credencial, token contextual ou payload sensível nos logs. Nenhum bypass de autenticação administrativa.

## Gatilhos de parada

Se a Spider não dispuser de extensão segura e pequena para o fluxo, se a mudança interferir no produto bancário, ou se a proposta exigir dados/coberturas Icatu não autorizados, parar essa trilha e relatar o bloqueio. Não substituir integração por animação, chamada simulada no frontend ou URL que apenas redireciona. A aprovação deste ADR não autoriza deploy, commit/push ou acesso a APIs privadas.
