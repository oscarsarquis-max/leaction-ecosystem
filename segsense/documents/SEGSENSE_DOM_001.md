# SEGSENSE_DOM_001 — Linguagem de domínio do catálogo local

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_DOM_001 |
| Título | Publicador, canal e ambiente contextual |
| Categoria | DOM — domínio |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 04/09/2026 |
| Dependências | SEGSENSE_ARQ_001 v0.3; SEGSENSE_PRM_004 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 04/09/2026 | Linguagem, invariantes e transições do catálogo administrativo local. |
| 1.1 | 04/09/2026 | Invariante: o publisher do ambiente é o mesmo do canal (V3). Oportunidade em `SEGSENSE_DOM_002`. |

## 1. Escopo

Este domínio descreve o primeiro módulo funcional **local** do SegSense: administração de publicadores, canais digitais e ambientes contextualizados.

Não pertencem a este domínio: link de publicação, jornada, intent, capability, execução, Spider, Icatu, mock de provedor, CNPJ, CPF, endereço, e-mail, telefone ou dados contratuais. A oportunidade contextual passou a `SEGSENSE_DOM_002` no PRM_005; permanece fora do aggregate de catálogo.

## 2. Publisher

Entidade que controla um ou mais canais de publicação.

| Campo | Regra |
|---|---|
| `id` | UUID |
| `key` | Identificador técnico imutável, normalizado para minúsculas, único globalmente, `^[a-z][a-z0-9-]{2,49}$` |
| `name` | Nome de exibição, espaços externos removidos, 3 a 120 caracteres |
| `status` | `DRAFT`, `ACTIVE`, `SUSPENDED` |
| `version` | Concorrência otimista persistida |
| `createdAt` / `updatedAt` | UTC |
| `createdBy` / `updatedBy` | Subject técnico autenticado recebido pela aplicação |

Disponibilidade efetiva: verdadeira somente se `status = ACTIVE`.

## 3. Channel

Canal digital pertencente a um Publisher.

| Campo | Regra |
|---|---|
| `id` | UUID |
| `publisherId` | Dono; toda busca valida este identificador |
| `key` | Imutável e única **dentro** do Publisher |
| `name` | 3 a 120 caracteres, trim |
| `type` | `WEBSITE`, `WEB_APPLICATION`, `MOBILE_APPLICATION`, `PARTNER_PORTAL` |
| `status` | `DRAFT`, `ACTIVE`, `SUSPENDED` |
| versionamento, timestamps e autoria | iguais ao Publisher |

Ativar um Channel exige Publisher `ACTIVE`. Disponibilidade efetiva: Channel `ACTIVE` **e** Publisher efetivamente disponível. Suspender o pai não altera o status persistido do filho.

## 4. ContextualEnvironment

Local lógico dentro de um Channel no qual, no futuro, poderá ser publicada uma oportunidade contextual. Este incremento **não** publica oportunidade.

| Campo | Regra |
|---|---|
| `id` | UUID |
| `publisherId` e `channelId` | Toda busca valida os dois |
| `key` | Imutável e única **dentro** do Channel |
| `name` | 3 a 120 caracteres, trim |
| `type` | `ARTICLE`, `PAGE`, `APPLICATION_SCREEN`, `EMBEDDED_COMPONENT` |
| `canonicalUrl` | Opcional; HTTPS absoluta; sem query, fragment, userinfo ou credencial |
| `status` | `DRAFT`, `ACTIVE`, `SUSPENDED` |

Não armazena conteúdo da página, texto editorial, perfil de usuário ou contexto inferido.

Ativar exige Publisher e Channel `ACTIVE`. Disponibilidade efetiva exige os três `ACTIVE` na cadeia.

## 5. Transições

```text
DRAFT → ACTIVE
ACTIVE → SUSPENDED
SUSPENDED → ACTIVE
```

Não existe retorno para `DRAFT`. Não existe exclusão física.

Reativar um pai **não** reativa filhos automaticamente.

## 6. Isolamento

Recurso fora do escopo informado (`publisherId` / `channelId`) é `NOT_FOUND` (404). Nunca 403 revelando existência.

O `publisher_id` de um ambiente **não** pode divergir do `publisher_id` do canal. A V3 impõe essa invariante no PostgreSQL por FK composta.

## 7. Autoria

Casos de uso exigem `CatalogActor.subjectId`. Sem adapter de identidade no runtime, os controllers administrativos permanecem inacessíveis. Testes usam autenticação mockada apenas no classpath de teste.
