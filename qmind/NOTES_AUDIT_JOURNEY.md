# Jornada visual da auditoria — decisões (2026-08-05)

## Decisões
- Fases da barra = `AssessmentStatus` existentes (draft→…→closed); sem 2ª máquina de estados.
- `/assessments/:id` = overview (mapa + dashboard + continuar).
- Wizard = preparação (`/guided`); trabalho operacional = `/work`; `/advanced` só para org_admin / consultant_auditor.
- Tipos `external_audit` e `certification_prep` adicionados ao CHECK SQL + enum Python (OpenAPI client ainda tipa união antiga — cast no create).

## Débitos
- Regenerar OpenAPI/`@qmind/api-client` para os novos tipos.
- Painel `/work` ainda reutiliza o Detail legado (IDs técnicos internos em alguns blocos).
- Checklist detalhado por fase além da preparação ainda é genérico (pendências derivadas de contagens).
- GET guided sem sessão em analysis+ → 404 (dashboard trata como vazio; não cria sessão).
