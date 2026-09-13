# SEGSENSE_LNK_001 — Link contextual seguro

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_LNK_001 |
| Título | Arquitetura do link contextual, token, emissão, resolução e revogação |
| Categoria | LNK — link |
| Versão | 1.2 |
| Status | Vigente nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_GOV_001; SEGSENSE_DOM_002; SEGSENSE_DAT_004; SEGSENSE_API_005; SEGSENSE_SEC_002; SEGSENSE_PRM_008 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Aggregate `PublishedContextLink`, token opaco, bindings do publicador e resolução pública mínima. |
| 1.1 | 11/09/2026 | Vínculo SQL à revisão aprovada e bindings amarrados à definição imutável. |
| 1.2 | 11/09/2026 | Página pública `/c/{token}` implementada no PRM_008. |

## 1. Fluxo

```text
Operador -> BFF SegSense -> token CSPRNG -> digest no PostgreSQL
                                   |
                                   +-> token bruto mostrado uma vez

Visitante -> /c/{token} -> BFF SegSense -> digest -> vínculo contextual interno
                                             |
                                             +-> envelope público mínimo
```

A URL pública `{SEGSENSE_PUBLIC_BASE_URL}/c/{opaqueToken}` é o identificador de navegação. A resolução HTTP é `GET /api/v1/public/context-links/{opaqueToken}`. A página React do visitante foi implementada no PRM_008.

## 2. Aggregate

`PublishedContextLink` é independente de `ContextualOpportunity`. Identidade estável (`id`) nunca entra na URL. Estados persistidos: `ACTIVE` e `REVOKED`. Expiração é efetiva por `expiresAt` (UTC), sem scheduler.

Emissão somente se a oportunidade estiver `PUBLISHED`, `effectivelyPublished=true`, revisão aprovada = corrente e janela aberta. O PostgreSQL (V8) rejeita link cuja `revision_number` não seja a `approved_revision` corrente, além das FKs de escopo e de revisão existente. Revogação é terminal (`expectedVersion` + justificativa 10–500). Pausar, revogar, expirar ou tornar a hierarquia indisponível impede a resolução mesmo com o registro `ACTIVE`. Retomada não ressuscita link revogado ou expirado.

Não há edição, reativação, rotação in-place nem recuperação de token.

## 3. Token

CSPRNG de 32 bytes (256 bits), Base64 URL-safe sem padding (43 caracteres). Persistência: SHA-256 binário UNIQUE. `tokenHint` = primeiros 8 caracteres, só apoio administrativo. Comparação por digest indexado; token malformado é rejeitado antes do hash, com o mesmo envelope 404.

## 4. Bindings

Coleção HTTP tipada `{fieldKey, value}` (não objeto livre). Somente campos `PUBLISHER` ou `EITHER` da revisão aprovada. `USER` nunca recebe valor. Obrigatórios `PUBLISHER` devem estar vinculados. `STATIC` não admite bindings. Snapshot imutável no link. O PostgreSQL (V8) exige que `field_key`, `field_type` e `field_source` coincidam com a definição da revisão vinculada.

## 5. Segregação

GOV_001 não define quarto papel de sujeito para emitir/revogar link. A emissão exige authority `segsense.link.manage`, não SoD adicional contra autor/aprovador/ativador.

## 6. Ausências

Sem Spider, Icatu, mock, consentimento, valor USER, materialização de `objectiveTemplate`, IA, produto, preço, cobertura ou elegibilidade.
