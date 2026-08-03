# QMind — Papéis e permissões

- Status: Aceito
- Data: 2026-08-03
- Congelamento: `domain-docs-v0`
- Depende de: `001_State_Machines.md`
- Precede: `../03_Database/001_Data_Dictionary.md`
- Base: ADR-002, ADR-006 Aceitos; `000_Domain_Model.md`
- Aceite: `../04_Docs/006_Domain_Acceptance_Checklist.md`

## 1. Princípios

1. **Negar por padrão.**
2. Toda decisão avalia: **organização ativa** + **papel(is) da Membership** + **ação** + **recurso** + **estado do recurso** + **relação** (autor, designado, revisor).
3. Papel não atravessa organização.
4. A interface não é fronteira de segurança.
5. Operações sensíveis e acessos excepcionais são auditados.

Legenda da matriz: **C** = criar/iniciar · **R** = ler · **U** = atualizar em estados editáveis · **T** = transição de estado permitida (conforme máquina) · **—** = negado · **※** = só se relação (autor/responsável/designado) · **‡** = com segregação (não pode ser o único ator da aprovação).

---

## 2. Papéis

| Código | Nome | Escopo típico |
|---|---|---|
| `platform_admin` | Administrador da plataforma | Multi-organização (excepcional, operações de plataforma) |
| `org_admin` | Administrador da organização | Toda a organização |
| `consultant_auditor` | Consultor / auditor | Avaliações em que participa; elaboração técnica |
| `quality_manager` | Gestor da qualidade | Governança do SG na organização; aprovações |
| `process_owner` | Responsável por processo | Processos sob sua responsabilidade; apoio a entrevistas |
| `action_owner` | Responsável por ação | Itens de ação designados a si |
| `reader` | Leitor / observador | Leitura autorizada; sem mutação de conteúdo técnico |

Um usuário pode acumular papéis **na mesma** Membership. A autorização efetiva é a união, ainda sujeita a guardas de estado e segregação.

---

## 3. Escopo organizacional

| Conceito | Regra |
|---|---|
| Tenant | `organization_id` da Membership ativa |
| Unidade | Filtro opcional; não substitui o tenant |
| Troca de organização | Só via seleção de Membership válida; nunca via body livre |
| Multi-org | Usuário autenticado escolhe contexto; tokens/sessão carregam org ativa |
| Dados de referência (norma) | Catálogo global **autorizado**; leituras sem vazar dados de cliente |

---

## 4. Matriz por recurso de domínio

### 4.1 Organização, unidades, processos, memberships

| Ação | platform_admin | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|---|
| Gerir Organization | C※ | U | — | R | — | — | R |
| Gerir Units | — | C/U | R | R | R | — | R |
| Gerir OrgProcess | — | C/U | C/U | C/U | U※ | — | R |
| Convidar / revogar Membership | ※ | C/U | — | R | — | — | — |
| Atribuir papéis org | ※ | U | — | — | — | — | — |

`platform_admin` cria organização apenas em fluxos de provisionamento; não edita conteúdo técnico do SG do cliente sem modo excepcional (sec. 6).

### 4.2 Avaliação (`Assessment`)

| Ação / transição | platform_admin | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|---|
| Criar / planejar (`draft`→`planned`) | — | C/T | C/T | C/T | R | — | R |
| Iniciar (`planned`→`in_progress`) | — | T | T | T | — | — | — |
| Conduzir campo (`in_progress`) | — | R | U/T | R | U※ entrevistas | — | R |
| Análise (`→ analysis`) | — | T | T | T | — | — | — |
| Abrir ações / relatório | — | T | T | T | — | — | — |
| Encerrar / cancelar | — | T | T※ | T | — | — | — |
| Reabrir `closed` | — | T‡ | — | T‡ | — | — | — |

Participação na equipe da avaliação pode restringir `consultant_auditor` a avaliações em que está designado (atributo de relação).

### 4.3 Evidência (`Evidence`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Autorizar upload / enviar | C | C | C | C※ | C※ | — |
| Aprovar quarentena (sistema ou operador) | T | T | T | — | — | — |
| Vincular a requisito/pergunta | U | U | U | U※ | U※ | — |
| Download / preview | R | R | R | R※ | R※ | R |
| Superseder versão | T | T | T | — | — | — |
| place_hold / release_hold (flag) | T | — | T | — | — | — |
| Descarte (`mark_disposal` / dispose) | T | — | T | — | — | — |

`platform_admin` não acessa binários de evidência sem sec. 6.

### 4.4 Constatação (`Finding`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Criar / editar `draft` | U | C/U | C/U | R | — | R |
| Submeter (`→ in_review`) | T | T※ autor | T | — | — | — |
| Aprovar (`→ approved`) | T‡ | — | T‡ | — | — | — |
| Rejeitar revisão | T | — | T | — | — | — |
| Retirar (`withdraw`) | T | T※ com quality_manager | T | — | — | — |

**Segregação:** quem aprova não pode ser o único autor da versão submetida (quatro olhos). `org_admin` só aprova se política da organização permitir e ainda assim ‡.

### 4.5 Plano de ação (`ActionPlan` / `ActionItem`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Criar plano / itens | C | C | C | — | — | — |
| Designar responsável | U | U | U | — | — | — |
| Executar item (`open`→…→`implemented`) | R | R | R | U※ | U※ | R |
| Validar implementação | T | — | T | T※ processo | — | — |
| Confirmar eficácia | T | — | T | — | — | — |
| Cancelar item/plano | T | T | T | — | T※ próprio open | — |

### 4.6 Relatório (`Report`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Elaborar `draft` | U | C/U | C/U | R | — | R |
| Submeter revisão | T | T※ | T | — | — | — |
| Discard (`draft`/`in_review`→`discarded`) | T | T※ draft | T | — | — | — |
| Publicar | T‡ | — | T‡ | — | — | — |
| Ler publicado | R | R | R | R | R | R |
| Nova versão / arquivar | T | T※ com quality_manager | T | — | — | — |

### 4.7 Processamento de IA (`Job` / `AiSuggestion`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Enfileirar Job (caso de uso permitido) | T | T | T | — | — | — |
| Cancelar Job próprio | T | T※ | T | — | — | — |
| Ver sugestão | R | R | R | R※ | — | — |
| Accept / edit / reject | T | T | T | — | — | — |
| Promover sugestão a conteúdo aprovado | — | — | — | — | — | — |

Promover a `Finding.approved` / `Report.published` **só** pelas transições humanas das seções 4.4 e 4.6.

Casos de uso de IA **proibidos** (independente de papel): declarar conformidade final; inventar evidência; publicar relatório; encerrar ação; alterar evidência aprovada; aprovar maturidade.

### 4.8 Maturidade (`MaturityAssessment`)

| Ação / transição | org_admin | consultant_auditor | quality_manager | process_owner | action_owner | reader |
|---|---|---|---|---|---|---|
| Elaborar `draft` / N/A | U | C/U | C/U | R※ | — | R |
| Submeter (`→ in_review`) | T | T※ | T | — | — | — |
| Aprovar | T‡ | — | T‡ | — | — | — |
| Rejeitar / rework (pré-aprovação) | T | T※ rework | T | — | — | — |
| Discard pré-aprovação | T | T※ draft | T | — | — | — |
| Superseder `approved` (nova versão) | T‡ | — | T‡ | — | — | — |

### 4.9 Mapa evento → autor (aceite)

Complementa as matrizes: para cada evento das máquinas, o autor autorizado está na coluna **Autor** de `001_State_Machines.md`. Este documento define o significado dos papéis, SoD (‡) e relações (※). Em conflito pontual, prevalece a **união** deste mapa com as guardas de estado; negação por padrão permanece.

Checklist de aceite exige percorrer Assessment, Evidence, Finding, ActionPlan/Item, Report, MaturityScore, Job/AiSuggestion e confirmar autor + cancel/reopen.

---

## 5. Segregação de responsabilidades

| Situação | Regra |
|---|---|
| Aprovação de constatação | Revisor ≠ autor da submissão |
| Publicação de relatório | Publicador ≠ único elaborador da versão (segundo par de olhos) |
| Validação de ação | Validador ≠ `action_owner` do item, salvo política explícita da organização com auditoria |
| Reabertura de avaliação `closed` | Exige `org_admin` ou `quality_manager` + motivo |
| Descarte de evidência | `org_admin` ou `quality_manager`; nunca o único uploader em hold legal |
| Autoaprovação por acúmulo de papéis | Se o mesmo usuário tem papéis que concentrariam autor+aprovador, o sistema **bloqueia** a transição ‡ |

---

## 6. Acessos administrativos excepcionais

### 6.1 `platform_admin`

Permitido sem modo especial:

- provisionar/desativar organização;
- configurar catálogo global de referenciais autorizados;
- operar feature flags, cotas e saúde da plataforma;
- ver metadados agregados sem conteúdo de evidência.

**Não permitido** por padrão: ler evidências, constatações, relatórios ou prompts completos de clientes.

### 6.2 Modo de suporte (break-glass)

| Controle | Exigência |
|---|---|
| Ativação | Justificativa, ticket/ID, duração máxima (ex. ≤ 4 h) |
| Escopo | Uma `organization_id` por sessão excepcional |
| MFA | Obrigatória |
| Visibilidade | Organização notificada quando política exigir |
| Auditoria | Quem, quando, o quê (IDs de recurso), motivo, expiração |
| Impersonação | Só se ADR/política futura autorizar; nunca silenciosa |
| Dados | Preferir metadados; download de evidência só se indispensável e registrado |

### 6.3 Contas de serviço

Identidade própria, escopo mínimo (ex.: trabalhador de quarentena, gerador de relatório), credenciais rotacionáveis, sem UI interativa.

---

## 7. Revogação e ciclo de vida

- Membership `revoked` ou expirada → negação imediata em todas as ações da organização.
- Autoria histórica permanece nos registros (`created_by`, aprovações).
- Último `org_admin` não pode ser removido sem transferir o papel.
- Sessões e tokens devem ser revogáveis (Cognito + sessão de aplicação).

---

## 8. Testes de autorização mínimos

1. Usuário da org A não lê avaliação da org B.
2. `reader` não muta Finding/Evidence/Report.
3. Autor não aprova a própria Finding.
4. `action_owner` só altera itens designados.
5. Job de IA da org A não recebe fontes da org B.
6. `platform_admin` sem break-glass não baixa evidência.
7. Após revoke, segunda requisição falha mesmo com ID conhecido.

---

## 9. Próximo documento

Com comportamento (estados) e autoridade (papéis) consolidados, o dicionário de dados em `../03_Database/001_Data_Dictionary.md` materializa entidades, chaves, `organization_id`, classificação, retenção e auditoria — ainda sem DDL de implementação.
