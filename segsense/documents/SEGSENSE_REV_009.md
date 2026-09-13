# SEGSENSE_REV_009 — Revisão de aderência do PRM_009

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_REV_009 |
| Título | Revisão de aderência do PRM_009 |
| Categoria | REV |
| Versão | 1.1 |
| Status | Corretivo único executado; etapa não autoaprovada |
| Data | 12/09/2026 |
| Dependências | SEGSENSE_PRM_009; SEGSENSE_FUN_002; SEGSENSE_DAT_005; SEGSENSE_API_006; SEGSENSE_SEC_003; SEGSENSE_UI_001 |

## 1. Etapa anterior

PRM_008 foi **aprovado com ressalvas**. Não houve corretivo `PRM_008_COR_001`. As sete ressalvas foram corrigidas no PRM_009. O PRM_009 recebeu o corretivo único `SEGSENSE_PRM_009_COR_001` (V10, idempotência, justificativa persistida, sessão no escopo da jornada).

## 2. SAT-01 a SAT-10

| SAT | Situação | Evidência |
|---|---|---|
| SAT-01 | PARCIAL | Identidade local `SEGSENSE`; envelope público inalterado na identidade |
| SAT-02 | PARCIAL | Manifesto preliminar inalterado |
| SAT-03 | NÃO IMPLEMENTADO | Satellite Contract não existe e não foi inventado |
| SAT-04 | PARCIAL | Browser → React → BFF; credencial de instância anônima ≠ autenticação de pessoa/satélite |
| SAT-05 | PARCIAL | Correlação HTTP local; evidência de decisão guarda `correlation_id` local |
| SAT-06 | NÃO APLICÁVEL NESTA ETAPA | Sem submissão de objetivo à Spider |
| SAT-07 | NÃO APLICÁVEL NESTA ETAPA | Sem execução para projetar |
| SAT-08 | PARCIAL | Deny-by-default; authorities `segsense.consent.*`; CORS PUT restrito; **sem** IdP |
| SAT-09 | ATENDIDO | Frontend só chama o BFF SegSense |
| SAT-10 | ATENDIDO | Aviso, instância e evidência são locais; nenhum client Spider/Icatu |

O satélite **não** é certificável.

## 3. Evidências funcionais

- Frontend: `npm ci`, `npm run lint`, `npm test` (**50** testes) e `npm run build` aprovados.
- Backend: `mvnw.cmd verify` completo, exit 0 — Testcontainers V1–V10 em banco vazio + `ContextInstanceIT` (justificativa, idempotência 409, SQL cruzado, append-only) + `CredentialCacheAbsenceTest`.
- Volume local `:5437` sem `down -v`: Flyway de v9 para **v10** no restart do profile `local`.
- Logo SHA-256: `CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D` (arquivo não editado).

## 4. Interface

- Sem aviso aprovado: CTA **Entender os próximos passos** (PRM_008).
- Com aviso: **Continuar com segurança** → transparência → sessão → campos → revisão → botão explícito de autorização + checkbox desmarcado que **não** substitui o botão → retirada.
- Credencial em `useRef` da jornada; limpa ao desmontar, trocar rota e retirar. Sem `localStorage`/`sessionStorage`/DOM.
- Aba administrativa **Finalidade e transparência**.
- Esta sessão não dispôs de ferramenta interativa de browser. Conferência visual humana das viewports 1440/768/390/320 permanece pendente.

## 5. Segurança

- Header da credencial; nunca query.
- Origin filter nas mutações públicas POST/PUT.
- Evidência sem valores pessoais; trigger impede UPDATE/DELETE de `consent_decision`.
- Não marcar conformidade legal como concluída.

## 6. Ausências confirmadas

Sem commit, push, deploy, alteração **feita por este corretivo** fora de `segsense/`, Spider, Panne, `.cursor/`, V1–V9 reescritas, campos pessoais, mock, Icatu ou Satellite Contract.

Limites residuais (não autoaprovam a etapa):

- Sem IdP: o fluxo de sucesso ponta a ponta no browser real não é exercível nesta etapa. Viewports 1440×900, 768×1024, 390×844, 320×568, zoom 200% e teclado **não** tiveram conferência visual humana nesta sessão (sem ferramenta de browser interativa).
- Recarregar ou fechar a página impede retomada; isso é o desenho, não um defeito residual do cache.
- HTTP real contra token inexistente responde 404 na criação antes de `IDEMPOTENCY_KEY_REQUIRED`; 400/409 estão cobertos no IT com link existente.
- A corrida concorrente é resolvida pela unique `context_instance_idempotency_unique` (INSERT duplicado → 409 sem segredo). O IT nomeado de corrida nesta entrega é replay sequencial da mesma chave.
- `npm ci` reportou 2 vulnerabilidades high no audit do lockfile; o lockfile não foi alterado neste corretivo.
- Conformidade jurídica / LGPD **não** está concluída.
