# Spider integration (placeholder)

O SegSense é o **Insurance Reference Satellite**. Isso define um **padrão de integração**, não incorporação. O backend Java (`segsense-backend`) exercerá a função de **Satellite BFF**. Runtime, banco, frontend e ciclo de vida do SegSense **não** pertencem à Spider. O projeto SegSense **não modifica** a Spider. O frontend nunca chamará a Spider diretamente e nunca armazenará credenciais técnicas da plataforma.

Quando houver contrato aprovado, o satélite enviará **objetivo e contexto** pelo **Satellite Contract**. O BFF não escolherá route, adapter, sistema executor nem Execution Plan: isso permanece no Core da Spider.

## Boundary atual

```text
Runtime: SIMULATED_INFRASTRUCTURE
Integrações: MOCK_ONLY
```

Nenhuma integração real está sendo declarada. Não há client HTTP, adapter, Satellite Contract executável, payload, timeout, credencial nem comportamento simulado neste diretório. O manifesto preliminar `DRAFT / NOT_CERTIFIED` vive no BFF SegSense apenas como configuração local; não é contrato aceito pela Spider e não é enviado a nenhum sistema.

O PRM_010 (ramo B) inspecionou o texto vigente da Spider e os schemas internos: o Satellite Contract externo permanece **AUSENTE**. Este diretório não recebe DTO, mapper ou client até `SEGSENSE_REQ_002` ser atendido.

## Regras

- capability não é sistema, rota ou adapter;
- não inventar endpoints, payloads, códigos de erro ou contratos;
- não acoplar o domínio SegSense a nomes internos de route/adapter da Spider;
- não criar máquina de estados operacional paralela à da Spider;
- qualquer ligação futura exige contrato versionado (`SPIDER-ARCH-017`) e decisão explícita.
