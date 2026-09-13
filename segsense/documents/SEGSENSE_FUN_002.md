# SEGSENSE_FUN_002 — Finalidade, transparência e manifestação versionada

## Controle

| Campo | Valor |
|---|---|
| Projeto | SegSense |
| Identificador | SEGSENSE_FUN_002 |
| Título | Fundamentos da finalidade, transparência e manifestação local |
| Categoria | FUN — fundamentos |
| Versão | 1.1 |
| Status | Vigente nesta etapa |
| Data | 12/09/2026 |

## 1. O que esta etapa demonstra

Uma pessoa que abre um convite contextual pode, quando houver aviso **aprovado** da revisão, iniciar uma sessão local, informar somente o necessário não pessoal, autorizar o uso **no SegSense** e retirar essa autorização enquanto a sessão estiver aberta.

Isto **não** equivale a consentimento jurídico válido, base legal LGPD completa, nem autorização para compartilhar dados com Spider, Icatu ou qualquer terceiro.

## 2. Agregados

| Agregado | Papel |
|---|---|
| `ConsentNotice` | Aviso versionado na revisão aprovada. DRAFT → versões imutáveis; APPROVED imutável e efetivo (um por revisão); RETIRED impede novas instâncias e preserva evidência. Aprovar e retirar exigem justificativa administrativa persistida em `consent_notice_decision`. |
| `ContextInstance` | Sessão anônima do convite. Estados: `AWAITING_INPUT`, `AWAITING_DECISION`, `AUTHORIZED`, `AUTHORIZATION_WITHDRAWN`, `EXPIRED`. |
| `ConsentDecision` | Ledger somente-append: `AUTHORIZED` e `WITHDRAWN`. |

## 3. Minimização

- Enum de classificação **não** foi expandido. Somente `NON_PERSONAL`.
- Sem nome, e-mail, telefone, CPF, endereço ou equivalentes em campos, fixtures ou exemplos.
- Valores do publicador não são perguntados de novo.
- Sem inferência ou enriquecimento.

## 4. Credencial da instância

CSPRNG ≥256 bits, Base64URL 43 caracteres, igual ao token de link. Valor cru uma vez no POST de criação (201). Frontend só em `useRef` da jornada ativa, limpo ao desmontar, trocar rota e retirar. Persistência: SHA-256 + hint. Mutações posteriores: header `X-SegSense-Instance-Credential`. Comparação em tempo constante. Recarregar ou fechar a página impede retomada nesta etapa; isso é dito antes de começar. Replay da criação responde 409 e não devolve o segredo.

## 5. Expiração

`expires_at` = mínimo entre expiração do link, `validUntil` da oportunidade e TTL configurado (`segsense.context-instance.ttl`, padrão 24 h).
