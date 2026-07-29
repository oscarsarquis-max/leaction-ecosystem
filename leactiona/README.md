# LeActiona (LEACTIONA.COM.BR)

LMS multimídia single-tenant — substitui Moodle. Artefatos Phanton: `PRD.md`, `SDD.md`, `SECURITY.md`.

> Raiz do código: `C:\Projetos\leaction-ecosystem\leactiona` (monorepo).

## Stack (v1)

| Camada | Tecnologia |
|--------|------------|
| API | Fastify + TypeScript |
| DB | PostgreSQL + Prisma |
| FE | Next.js (export estático) + Tailwind — módulos seguintes |
| LRS | Learning Locker (externo) |
| PII | AES-256-GCM (app-level) + `emailHash` HMAC |

## Setup local

```powershell
cd C:\Projetos\leaction-ecosystem\leactiona
docker compose -f database/docker-compose.yml up -d
copy .env.example .env   # preencher PII_ENCRYPTION_KEY (32 bytes base64)
npm install
npx prisma migrate deploy
npx prisma generate
npm run test:db
npm run test:auth
npm run test:lms
npm run test:player
npm run test:gami
npm run test:cert
npm run dev              # API http://127.0.0.1:5020/health
# frontend: cd frontend && npm i && npm run dev  → http://127.0.0.1:3020
```

Postgres local: `127.0.0.1:5436` · db/user `leactiona`.

## Auth (prompt 2)

| Método | Rota | Notas |
|--------|------|--------|
| POST | `/api/v1/auth/login` | JWT RS256 ≤15min + refresh; body PKCE S256; header `DPoP` |
| POST | `/api/v1/auth/token` | refresh + `code_verifier` + `DPoP` |
| GET | `/api/v1/admin/ping` | somente `ADMIN` |

Papéis: `ADMIN` · `TEACHER` · `STUDENT` (single-tenant `organization_id=global`).

## LMS (prompt 3)

| Método | Rota | Notas |
|--------|------|--------|
| GET | `/api/v1/courses` | free + pagos com `is_paid_access` |
| GET | `/api/v1/lessons/:id` | BOLA; pago só com matrícula `is_paid_access=true`; URL assinada |
| CRUD | `/api/v1/courses`, `/modules`, `/lessons` | ADMIN/TEACHER |
| POST | `/api/v1/admin/enrollments` | matrícula manual + audit log |
| DELETE | `/api/v1/admin/users/:id` | LGPD + audit log |

Sem gateway de pagamento.

## Player + xAPI (prompt 4)

| Método | Rota | Notas |
|--------|------|--------|
| POST | `/api/v1/xapi/statements` | proxy autenticado → Learning Locker |
| POST | `/api/v1/xapi/video-completed` | statement `completed` + envio LRS |
| POST | `/api/v1/xapi/webhook` | sync progresso; HMAC `X-LRS-Signature` |

Frontend: `MediaPlayer` (YouTube/Vimeo + overlays), `ScormH5pFrame`, fila offline `xapi-queue`. Demo: `/demo/player/`.

## Gamificação (prompt 5)

Pontuação, badges e ranking **somente no servidor** (input de pontos do cliente é ignorado). Idempotência via `LessonCompletion` unique + advisory lock por usuário.

| Método | Rota | Notas |
|--------|------|--------|
| POST | `/api/v1/lessons/:id/complete` | progresso + pontos; badge `course_complete_{id}` a 100% |
| POST | `/api/v1/courses/:courseId/assessment-result` | nota server-side; badge `perfect_score_{id}` |
| GET | `/api/v1/gamification/ranking` | ranking global (sem PII) |
| GET | `/api/v1/gamification/me` | perfil + badges do aluno |

`video-completed` (xAPI) também chama a mesma lógica de conclusão de lição.

## Certificados (prompt 6)

PDF gerado on-the-fly com `pdfkit` e enviado como stream autenticado (sem página pública / QR). Elegibilidade recalculada no servidor: 100% das lições; se houver nota registrada, exige ≥ `Course.minGrade` (default 70). Sem nota (=0) = provisório “curso sem avaliação” até o SDD ganhar Assessment.

| Método | Rota | Notas |
|--------|------|--------|
| GET | `/api/v1/certificates/:courseId/status` | habilita botão sem gerar PDF |
| GET | `/api/v1/certificates/:courseId/download` | JWT+DPoP; PDF em buffer |

Desvios / feedback Phanton: `docs/LOG-DESVIOS.md`, `docs/retorno-para-phanton.md`, `docs/ENTREGA-TEMPLATE.md`.

## Organização

Uma única `Organization` com id `global` — sem multi-tenant.
