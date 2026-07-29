# Retorno para o Phanton — lições da LeActiona

Avaliação de produto (LMS single-tenant, sem billing) usada para construir a plataforma **e** pressionar o pipeline Phanton. Destinatário: Oscar / fase de reaprovação.

## 1. O que o Phanton acertou

- Fila `module_prompts` com deps e status (`liberado` → `entregue`) funciona como ritmo de entrega.
- Separação PRD → SDD → security → prompts é a topologia certa.
- UI já tem **Copiar prompt** (`CopyableBlock` / `ModulePromptQueue`) — não reinventar; estender.

## 2. Falhas estruturais (prioridade)

### P0 — Entidades de avaliação ausentes no SDD

O pedido inicial e o PRD citam avaliações. O SDD não modela `Assessment` / `Attempt` / `Question` / `ItemResponse`. Consequência em **quatro** módulos:

| Módulo | Sintoma |
|--------|---------|
| LMS | `Enrollment.averageGrade` sem origem |
| xAPI | `passed`/`failed` sem nota canônica |
| Gamificação | “nota mínima” / `PERFECT_SCORE` sem evento real |
| Certificado | regra provisória: nota 0/nula = “sem prova” (vira buraco quando Assessment existir) |

**Ajuste**: em `phase_sdd.py` / quality_score, se PRD mencionar avaliação/quiz/certificado+nota → checklist obrigatório de entidades. Não basta prosa livre no “Modelo de Dados”.

### P0 — Módulo frontend descritivo inexistente

`build_order` enviesa “serviços”. Player/SPA/Next ficam implícitos ou só pedaços (ex.: “player-xapi”) sem:

- rotas/páginas (catálogo, lição, ranking, certificado, admin)
- contratos de API consumidos por tela
- estados de loading/erro/offline
- CSP do SPA vs CSP da API
- testes de UI mínimos (render, gate visual do botão de certificado)

**Ajuste**:

1. Campo `camada: backend | frontend | shared` em `build_order`.
2. Regra: se PRD tem UI/player/portal → ≥1 módulo `*-frontend` / `*-ui` / `*-player` com deps nos módulos de API.
3. `prompt_cursor` gera prompt de frontend com: telas, componentes, integração auth, fora de escopo (design system genérico), testes_requeridos de UI.

### P1 — FAPI 2.0 / PKCE / DPoP em produto não financeiro

LMS sem Open Banking. Pedido inicial: **sem pagamento**. Ainda assim `security_guidelines` empurrou FAPI + PKCE + DPoP.

- PKCE sem authorization code = cerimônia vazia.
- DPoP em SPA estático = chave no browser; custo alto vs benefício para ~centenas de alunos.
- Alternativa proporcional: access curto + refresh opaco rotativo + detecção de reuso + cookie httpOnly.

**Ajuste** em `security_domain.py`:

- Separar `financeiro_generico` vs `open_finance`.
- FAPI/PAR/mTLS/DPoP **só** se houver Open Banking / consentimento bancário / APIs reguladas.
- Perfil `educacao`: LGPD, isolamento de conteúdo, ASVS auth — **sem** FAPI default.
- Exemplar do LLM de security não deve ensinar FAPI como texto-padrão de todo módulo auth.

### P1 — Single-tenant vs `organization_id`

Prompt pede single-tenant; schema com `organization_id` (mesmo fixo `global`) colide com testes “proibir colunas tenant” de outra implementação. Phanton deve escolher **uma** redação:

- A) zero coluna de tenant; ou  
- B) coluna fixa documentada + teste de invariante `= global` / uma linha em `organizations`.

### P2 — Security guidelines incompletas onde importa

Incluir explicitamente (hoje vêm só da improvisação do implementador):

- `postMessage` origin+source (player/SCORM)
- sanitização PDF (bidi / controles), não só “HTML”
- CORS allowlist obrigatória quando FE ≠ origem da API
- query log ORM proibido se parâmetros carregam PII pré-cifra
- ranking: o que é PII público (nome completo vs inicial vs anônimo)
- webhook: raw body + janela de tempo + comparação constant-time

### P2 — Forma de cópia em **todas** as entregas

Hoje: copiar prompt/Cursor funciona bem. Falta padronizar:

| Entrega | Copiar |
|---------|--------|
| PRD / SDD / SECURITY | botão “Copiar markdown completo” (já parcial) + **download .md pack** |
| Cada `module_prompt` | já tem Copiar — manter + “Copiar prompt + testes + segurança” como um bloco |
| Marcar entregue | opcional: anexar/colar `LOG-DESVIOS` snippet (template) |
| Artefato final | “Exportar pasta docs/” (zip ou lista de arquivos) |

Template de sessão do implementador: `leactiona/docs/ENTREGA-TEMPLATE.md` — Phanton pode linkar esse formato no rodapé de cada módulo liberado.

## 3. Redações sugeridas (snippets)

### RN02 (acesso pós-conclusão)

> Matrícula **não cancelada** (`ACTIVE` ou `COMPLETED`) com `is_paid_access = true` libera conteúdo pago. `CANCELLED`/`REVOKED` não libera.

### RN03 (amostra)

> `Course.is_free` **ou** `Lesson.is_free_preview` libera a lição sem matrícula paga; não atravessa conteúdo despublicado.

### RN11 (ranking + LGPD)

> Ranking não exibe nome completo por default. Modos: `short` | `anonymous` | `full` (este último exige decisão explícita de produto/consentimento).

### SDD — Assessment (mínimo)

```
Assessment { id, courseId, title, minScore, maxAttempts }
Attempt { id, assessmentId, userId, score, submittedAt }
Enrollment.averageGrade ← derivado dos Attempts aprovados do curso
```

### security_guidelines — auth LMS (substituir FAPI)

> Access JWT vida curta (≤15 min). Refresh opaco, hash no banco, rotação + revogação de família em reuso. Cookie httpOnly Secure SameSite=Strict nas rotas de auth **ou** storage documentado. PKCE/DPoP apenas se houver AS externo / authorization code.

## 4. O que **não** pedir ao Phanton

- Reescrever a LeActiona do zero na outra árvore do agente.
- Mandatar Argon2 vs bcrypt no prompt (deixar “Argon2id ou bcrypt” + OWASP).
- Detalhe de Docker Compose / vitest series (só código).

## 5. Critérios de aceite da melhoria no Phanton

1. Pipeline LMS de teste gera `build_order` com ≥1 módulo frontend descritivo.
2. SDD do mesmo pipeline contém entidades de Avaliação.
3. `security_guidelines` de prompt “LMS sem pagamento” **não** cita FAPI 2.0.
4. Toda tela de artefato (PRD, SDD, security, module prompt) tem ação de cópia óbvia; module prompt copia bloco único (requisitos+testes+segurança).
5. Teste automatizado Phanton cobre (1)–(3).

## 6. Status de implementação no Phanton (2026-07-29)

Implementado em `phanton/`:

- Domínio `educacao` + security sem FAPI; FAPI só com Open Finance/PIX
- `build_order[].camada` + injeção de `app-frontend` se PRD tem UI
- Checklist Assessment anexado ao SDD quando PRD cita avaliações
- UI: botão **Copiar entrega** (prompt + testes + template de desvios)

Critérios 1–4 da seção 5 cobertos por testes em `test_security_guidelines.py` e `test_sdd_quality.py`.
