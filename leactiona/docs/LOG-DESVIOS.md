# Log de desvios e modificações — LeActiona (monorepo)

Registro do que esta implementação fez **diferente** dos artefatos Phanton (PRD, SDD, `module_prompt`) e do cruzamento com a avaliação técnica de outro agente (2026-07-29).

**Regra**: toda sessão que altera o projeto acrescenta entradas aqui antes de encerrar.

## Legenda

| Tipo | Significado |
|------|-------------|
| `LACUNA` | Artefato não previu |
| `CONFLITO` | Artefato contraditório; resolvido pela intenção |
| `INFRA` | Decisão de ferramenta/infra |
| `CORREÇÃO` | Bug nosso corrigido depois |
| `BACKLOG` | Achado válido; ainda não adotado nesta árvore |

**Incorporar em**: PRD · SDD · `security_guidelines` · prompt do módulo · Phanton (pipeline) · só código

---

## Cruzamento com avaliação do outro agente

| Item (outro agente) | Nesta `leactiona` | Ação |
|---------------------|-------------------|------|
| 1.1 HMAC lookup + ciphertext | ✅ `emailHash` + `emailEnc` (CPF só ciphertext — lookup CPF não há) | Manter; Phanton deve exigir lookup p/ campos pesquisáveis |
| 1.2 `LessonProgress` + SCORM resume | Parcial: `LessonCompletion` (sem `scormLocation`/`suspendData`) | BACKLOG SCORM state |
| 1.3 `AnonymizedProgressStat` | ❌ | BACKLOG módulo LGPD |
| 1.4 pontos/nota configuráveis no Course | Parcial: `minGrade`; pontos ainda em `Lesson.pointsOnComplete` | Alinhar nomes; aceitar |
| 1.5 `MediaType.HTML5` | ❌ falta | BACKLOG |
| 1.6 preview/obrigatória/slug | ❌ | BACKLOG produto |
| 1.7 Prisma query log off | ✅ aplicado (era ON em dev) | CORREÇÃO |
| 1.8 teste anti-colunas tenant | ❌ temos `organization_id=global` | CONFLITO single-tenant vs coluna org — ver Phanton |
| 1.10 CORS | ✅ allowlist `CORS_ALLOWED_ORIGINS` | LACUNA fechada |
| 2.1 FAPI/PKCE/DPoP | ⚠️ implementados (teatro proporcional ao prompt) | Phanton: retirar FAPI de LMS; nós: manter até decisão de produto |
| 2.2 ES256 vs RS256 | RS256 | INFRA; ES256 ok se SDD permitir |
| 2.3 Argon2id | bcrypt | BACKLOG migrar |
| 2.6 refresh family + lockout | refresh+PKCE+DPoP; sem lockout/family reuse | BACKLOG |
| 2.8 admin cria usuários | parcial (seed/create) | Verificar |
| 3.1 COMPLETED mantém acesso | ✅ ACTIVE+COMPLETED | OK |
| 3.2 `isFreePreview` | ❌ | BACKLOG |
| 3.8 AuditLog hash-chain + triggers | AuditLog simples append | BACKLOG imutabilidade forte |
| 4.1 xAPI via backend | ✅ | OK |
| 4.3 outbox xAPI | ❌ fila só client | BACKLOG |
| 4.8 runtime SCORM completo | parcial (frame + sanitize) | BACKLOG validação pacote real |
| 5.1 `PointAward` ledger | contador + `LessonCompletion` unique | Aceitável curto prazo; ledger melhor |
| 5.3 ranking sem nome completo | ✅ só `user_id` | OK (mais restrito que “Maria S.”) |
| 5.13 entidades Avaliação | ❌ gap Phanton | Prioridade Phanton |
| 6.1 nota do curso | ✅ `Course.minGrade` | OK |
| 6.2 nota nula = sem avaliação | ✅ regra provisória `averageGrade<=0` | Documentado; quebra quando Assessment existir |
| 6.4 sanitização bidi PDF | ✅ | CORREÇÃO |
| 6.12 `/certificates/.../status` | ✅ | LACUNA fechada |
| Módulo frontend descritivo | ❌ Phanton não gerou | Ver `retorno-para-phanton.md` |

---

## Sessão 2026-07-29 (pós-avaliação cruzada)

### S1 — Prisma query log desligado
**Tipo**: CORREÇÃO · **Incorporar em**: prompt / security  
Query log emite parâmetros pré-cifra. Desligado em todos os ambientes.

### S2 — CORS allowlist
**Tipo**: LACUNA · **Incorporar em**: SDD §2  
`@fastify/cors` + `CORS_ALLOWED_ORIGINS`. Em `NODE_ENV=production` exige a variável.

### S3 — Certificado: nota 0 = curso sem avaliação (provisório)
**Tipo**: CONFLITO · **Incorporar em**: SDD (Assessment)  
Enquanto não existir entidade de avaliação, `averageGrade <= 0` não bloqueia certificado se progresso = 100%. Quando Assessment chegar, exigir nota se o curso tiver avaliações.

### S4 — Sanitização PDF bidi + status endpoint
**Tipo**: LACUNA · **Incorporar em**: security_guidelines / SDD §4  
Controles + overrides Unicode; `GET /api/v1/certificates/:courseId/status`.

---

## Backlog priorizado (não fazer tudo de uma vez)

1. **Assessment / Attempt / Question** (desbloqueia gamificação + certificado corretos)
2. `LessonProgress` SCORM (`location`, `suspend_data`) + runtime real
3. LGPD: `AnonymizedProgressStat` + fluxo delete
4. Auth: refresh rotation + reuse detection (substituir DPoP se produto aceitar)
5. AuditLog HMAC-chain + triggers
6. `PointAward` ledger
7. Módulo frontend (catálogo, player shell, área do aluno) — depende do Phanton gerar o prompt
8. CORS/CSP alinhados ao CDN do player

Feedback estruturado para Oscar: [`retorno-para-phanton.md`](./retorno-para-phanton.md).  
Template de entrega com bloco copiável: [`ENTREGA-TEMPLATE.md`](./ENTREGA-TEMPLATE.md).
