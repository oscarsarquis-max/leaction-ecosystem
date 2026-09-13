# SEGSENSE_PRM_009 — Consentimento versionado e coleta progressiva local

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_PRM_009 |
| Título | Consentimento versionado, minimização e coleta progressiva local |
| Categoria | PRM — prompt original |
| Versão | 1.0 |
| Status | Executado nesta etapa |
| Data | 11/09/2026 |
| Dependências | SEGSENSE_PRM_008 (aprovado com ressalvas); SEGSENSE_API_005; SEGSENSE_DAT_004; SEGSENSE_SEC_002; SEGSENSE_UI_001 |

## Histórico de versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0 | 11/09/2026 | Prompt original da etapa; correções herdadas do PRM_008 incorporadas. |

## 1. Correções herdadas do PRM_008

Não foi criado `SEGSENSE_PRM_008_COR_001`. As ressalvas aprovadas foram corrigidas nesta etapa e registradas em `SEGSENSE_REV_009`:

1. `HumanStatus` em 320 px empilha o marcador acima do título.
2. Foco de rota em `#main-content`, sem outline permanente no `h1`.
3. Abas: setas movem seleção e foco; Home/End; aba **Finalidade e transparência**.
4. `CopyOnceLink` anuncia falha de clipboard sem sucesso falso.
5. Chaves React públicas estáveis (`fieldKey` / `key`).
6. Superfícies de status perigo/aviso nos tokens `--segsense-*`.
7. Logo admin em 72 px com `object-fit: contain`, PNG intacto.

## 2. Objetivo

Jornada pública progressiva **dentro do SegSense**:

1. `ContextInstance` local vinculada ao link, oportunidade, revisão aprovada e versão do aviso.
2. Coleta somente de campos USER/EITHER + NON_PERSONAL da revisão imutável, sem repetir EITHER já ligado pelo publicador.
3. Finalidade/transparência versionada (`ConsentNotice`).
4. Manifestação explícita da pessoa.
5. Retirada durante a sessão contextual.
6. Evidência imutável minimizada.

Isto demonstra tecnicamente uma manifestação versionada. **Não** é “consentimento LGPD válido”.

## 3. Fora de escopo

Satellite Contract, Spider, Icatu, mock, produto, elegibilidade, cotação, contratação, campos pessoais/sensíveis, IA, IP/UA/fingerprint como evidência, commit/push/deploy.

## 4. Entrega desta execução

- V9 incremental (V1–V8 intactas).
- Domínio `ConsentNotice` / `ContextInstance` / `ConsentDecision`.
- APIs admin do aviso e mutações públicas da instância.
- Credencial opaca da instância (CSPRNG, SHA-256, header `X-SegSense-Instance-Credential`).
- CORS PUT + headers da instância; filtro de Origin / Sec-Fetch-Site nas mutações públicas.
- Jornada pública progressiva e aba administrativa de finalidade.
- Documentos FUN_002, DAT_005, API_006, SEC_003, REV_009, UI_001 v1.1, PLN_001 v1.8.

## 5. Linguagem

Público: “autorização”, “sua escolha”, “retirar autorização”. Nomes de domínio: `ConsentNotice`, `ConsentDecision`, `ConsentEvidence` (ledger `consent_decision`). Sem checkbox pré-marcado, aceite implícito ou dark pattern.
