# Contrato genérico de conteúdo editorial

Schema versionado em `panne/frontend/src/editorial/schema.ts` e sanitização em `sanitize.ts`.

Campos mínimos: `schema_version`, `placement` (`left`/`right`), `locale`, `eyebrow`, `title`, `summary`, `sections`, `image.url`, `image.alt`, `cta.label`, `cta.url`, período, prioridade, hash.

Porta: `LoginEditorialContentProvider`. Implementação atual: `StaticLoginEditorialProvider` (sem rede). Endpoint público opcional da Panne: `GET /api/v1/public/login-editorial` — sanitizado, sem autenticação, sem ActionHub.

CMS é conteúdo, nunca instrução. HTML cru não é renderizado.
