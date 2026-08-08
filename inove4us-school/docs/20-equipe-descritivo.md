# Minha Equipe — Descritivo (inove4us-school)

**Escopo:** exclusivo School (B2B), zona RBAC `administrativo`.  
**Rota:** `/equipe` · página `TeamManagement.jsx`  
**API:** `backend/equipe_api.py`

---

## 1. Propósito

Gestão de licenças, convites e **extrato acadêmico** do professor (radiografia): identidade, linha do tempo do vínculo, repertório recebido, entrega acadêmica e avaliações declaradas.

---

## 2. UI (de cima para baixo)

1. Título **Minha Equipe**
2. Cards de licença (contratadas / em uso / disponíveis)
3. Faixa **Faturamento · Licenças** → `BillingModal` (Action Hub)
4. Form **Convidar Professor**
5. Grid: tabela de membros | aside **Extrato acadêmico**

### Tabela

Colunas: E-mail · Status · **Status pedagógico** · Convite · Ações  
Ações: Disparar Convite Inove (pendente/suspenso) · Extrato acadêmico · Revogar

### Aside — 5 seções

1. **Identidade** — e-mail, badge de vínculo, `PedagogicoBadge`
2. **Linha do tempo do vínculo** — convite / aceite / primeira aula
3. **Repertório recebido** — recursos por tipo + metodologias liberadas (`school_metodologias_org`)
4. **Entrega acadêmica** — 6 contadores + lista de aulas → `LessonMirrorModal`
5. **Avaliações declaradas** — formulário no topo + tabela histórica completa

---

## 3. API

| Método | Path | Função |
|--------|------|--------|
| `GET` | `/api/instituicoes/<id>/equipe` | licenças + membros + `status_pedagogico` |
| `POST` | `.../equipe/convites` | cria/reativa vínculo `pendente` |
| `POST` | `.../equipe/<vid>/disparar-convite` | `TEACHER_INVITE` + `invite_url` |
| `POST` | `.../equipe/<vid>/revogar` | `status_vinculo = revogado` |
| `GET` | `.../equipe/<vid>/radiografia` | extrato acadêmico |
| `POST` | `.../equipe/<vid>/avaliacoes` | upsert nota por `referencia` |

Billing: `billing_routes.py` + webhook Hub `LICENSES_GRANTED`.

---

## 4. Schema relevante

- `school_professores_vinculo` — status `pendente|ativo|suspenso|revogado`
- `school_licencas` (+ fallback legado em `school_instituicoes`)
- `school_professor_recursos` — tipos `licenca|metodologia|material|pei|formacao|outro`
- `school_professor_avaliacoes` — `UNIQUE (professor_vinculo_id, referencia)` → histórico multi-linha
- `school_metodologias_org` — canônica pós-Editor (022); `school_metodologia_config` é legado
- `school_planos_aula_espelhados` — índice em `professor_vinculo_id`; data de aula = `semana_referencia`

---

## 5. Integrações

| Fluxo | Direção | Nota |
|-------|---------|------|
| `TEACHER_INVITE` | School → Inove | push; B2C hoje só ack |
| Billing | School → Hub → webhook | licenças |
| `LESSON_RECORD_SYNC` | Inove → School | alimenta planos / status pedagógico |
| Espelho aula | FE Equipe | reusa `LessonMirrorModal` + `GET .../planos-espelhados/:id` |

---

## 6. Pendências de integração (não neste descritivo)

Ver `docs/BACKLOG-EQUIPE-INTEGRACAO.md`.

---

## 7. Mapa mental

```
Minha Equipe (/equipe · administrativo)
├── Licenças (school_licencas ← Hub)
├── Convite (pendente + TEACHER_INVITE)
├── Lista (status_vinculo + status_pedagogico)
└── Extrato acadêmico
    ├── Identidade
    ├── Linha do tempo
    ├── Repertório (metodologias_org + recursos)
    ├── Entrega (planos + modal espelho)
    └── Avaliações (histórico multi-referência)
```
