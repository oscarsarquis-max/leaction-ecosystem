# Secretaria Acadêmica — Descritivo / Inventário (inove4us-school)

**Escopo:** exclusivo School (B2B), zona RBAC `operacional`.  
**Rota ativa:** `/secretaria` · página `SecretariaOperacional.jsx`  
**APIs ativas da UI:** `backend/secretaria_routes.py` (`/api/secretaria/*`)

Base para reformulação no mesmo padrão do Radar e da Equipe (`20-equipe-descritivo.md`).

---

## 1. Frontend

| Item | Detalhe |
|------|---------|
| Página ativa | `frontend/src/pages/SecretariaOperacional.jsx` |
| Rota | `/secretaria` em `App.jsx` (`ZoneGate` zona `operacional`) |
| Nav | `rbac.js` → `{ to: '/secretaria', label: 'Secretaria Acadêmica', zonas: [operacional] }` |
| Legado órfão | `Secretaria.jsx` — **não** está em `App.jsx`; usa API hierárquica `/api/instituicoes/...` |
| Auxiliares (mesmo arquivo) | `Modal`, `Field`, tabs via `tabClassNameCompact` |
| Externos | só `useAuth` |

**Abas (5)**
1. Unidades — tabela + modal Novo  
2. Períodos Letivos — tabela + modal Novo  
3. Disciplinas — tabela + modal Novo (catálogo flat)  
4. Alocação Docente — formulário inline + tabela de alocações  
5. Mural / Comunicações — formulário inline + lista

**Sem:** edição, exclusão, desativação, filtros, KPI, aside/detalhe, paginação.  
**Create-only** em unidades/períodos/disciplinas; alocação e comunicação só criação (+ status B2C na lista).

---

## 2. Backend — duas superfícies

### 2.1 Operacional (UI atual) — `secretaria_routes.py`

| Método | Path | Propósito |
|--------|------|-----------|
| `GET/POST` | `/api/secretaria/unidades` | CRUD parcial (list + create) |
| `GET/POST` | `/api/secretaria/periodos` | list + create (`rotulo` ← `nome`) |
| `GET/POST` | `/api/secretaria/disciplinas` | catálogo flat (`curso_id` NULL) |
| `GET` | `/api/secretaria/professores` | dropdown Equipe (`ativo`/`pendente`) |
| `GET/POST` | `/api/secretaria/alocacoes` | alocação + `TEACHER_ALLOCATED` |
| `GET/POST` | `/api/secretaria/comunicacoes` | mural + push B2C |
| `PATCH` | `/api/secretaria/comunicacoes/<id>` | status (sem UI) |

Auth: `@require_gestor` (sessão `school_gestor`).

### 2.2 Hierárquica (legado / `Secretaria.jsx`) — `secretaria_api.py`

Cadeia: unidade → período → **curso** → disciplina + calendário letivo.  
Paths: `/api/instituicoes/<id>/unidades`, `periodos-letivos`, `/api/periodos-letivos/<id>/cursos`, etc.  
**Ainda registrada** em `app.py`, mas **fora** da rota `/secretaria` atual.

### 2.3 Paralelo

`comunicacoes_api.py` — `/api/instituicoes/<id>/comunicacoes` (mesma tabela; usado pela UI órfã).

---

## 3. Schema / tabelas

| Tabela | Migration | Papel |
|--------|-----------|--------|
| `school_unidades` | 008 | Campi / unidades |
| `school_periodos_letivos` | 015 | Período (`rotulo`, datas, status, `unidade_id` opcional) |
| `school_cursos` | 015 | Curso no período — **sem UI** na Secretaria operacional |
| `school_disciplinas` | 015 + 019 | Flat (`instituicao_id`, `curso_id` nullable) ou sob curso |
| `school_alocacoes_docentes` | 019 | unidade+período+disciplina+vínculo; `notificado_b2c` |
| `school_comunicacoes_eventos` | 013 | mural/eventos; `replicado_b2c` |
| `school_calendario_letivo` | (secretaria_api) | calendário — sem UI operacional |
| `school_professores_vinculo` | 001/014 | fonte do dropdown de alocação |
| `school_avisos_mesa` | 027 | **outro** canal (Radar → pin na Mesa); não é a aba Mural |

Produto: **sem alunos** na Secretaria (comentários 015).

---

## 4. Integrações

| Fluxo | Direção | Mecanismo |
|-------|---------|-----------|
| **TEACHER_ALLOCATED** | School → Inove | `dispatch_teacher_allocated` → webhook; B2C cria compromisso em `inove_agenda_eventos` |
| **Comunicado / mural** | School → Inove | `push_comunicado_to_b2c` → `POST /api/integracoes/school/comunicados` (API key) → mural + agenda |
| Público `unidade` | — | **Não filtra** vínculos por unidade (comentario no código: sem vínculo unidade↔professor) |
| `professor_b2c_id` | — | push usa UUID provisório ou id numérico se `isdigit()` — mesmo gap da Equipe |
| Avisos Mesa (Radar) | School → Inove | `AVISO_MESA_PINNED` / `school_avisos_mesa` — canal **separado** do mural |

---

## 5. UX atual (fluxo)

1. Abrir `/secretaria` → 6 GETs em paralelo.  
2. Cadastrar unidade / período / disciplina (modais).  
3. Alocar: escolher 4 combos → POST → feedback + flag Notificado/Pendente.  
4. Publicar mural → POST status `publicado` → push B2C.  
5. Sem fluxo de cancelar comunicado, desfazer alocação ou editar cadastros.

---

## 6. Gaps / TODOs

1. **UI órfã** `Secretaria.jsx` + API hierárquica vs flat operacional — dois modelos mentais.  
2. **Cursos** existem no schema/API hierárquica, invisíveis na UI atual.  
3. **Só create** — sem edit/delete/soft-delete nas abas.  
4. **PATCH comunicações** sem UI (cancelar/republicar).  
5. **Público `turma`** no schema; FE só oferece professores / toda instituição / unidade.  
6. **Público unidade** não filtra destinatários.  
7. **Alocação de professor pendente** permitida (mesmo gap `pendente→ativo` da Equipe).  
8. **Dois canais de aviso:** Mural (Secretaria) vs Quadro de Avisos (Radar / pin Mesa).  
9. Sem descritivo de produto anterior no repo (este arquivo é a base).

---

## 7. RBAC

- Zona: **`operacional`**.  
- Qualquer gestor com a zona cria unidades/aloca/publica — sem granularidade por ação.

---

## 8. Mapa mental

```
Secretaria Acadêmica (/secretaria · operacional)
├── Unidades (school_unidades)
├── Períodos (school_periodos_letivos)
├── Disciplinas flat (school_disciplinas.instituicao_id)
├── Alocação → TEACHER_ALLOCATED → agenda B2C
├── Mural → school_comunicacoes_eventos → mural B2C
└── [legado] cursos + calendário + Secretaria.jsx (fora da rota)
```

## 9. Próximo passo sugerido

Prompt de reformulação (Claude → Cursor), no mesmo formato da Equipe:  
definir se a superfície oficial é **flat operacional**, **hierárquica com cursos**, ou híbrido; o que fazer com `Secretaria.jsx`; unificar ou separar Mural vs Avisos da Mesa; e quais CRUDs entram no escopo.
