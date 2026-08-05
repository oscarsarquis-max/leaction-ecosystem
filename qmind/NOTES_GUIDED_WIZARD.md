# Assessment Wizard — decisões e débitos (2026-08-04)

## Decisões
- Catálogo file-backed `catalog_iso9001_c4c5_v1.json` (cláusulas 4–5); perguntas próprias em pt-BR.
- Sessão 1:1 com avaliação (`guided_sessions` + `guided_answers`), RLS por `organization_id`.
- Entrada draft/planned → `/assessments/:id/guided`; painel legado em `/advanced` ou status posteriores.
- API client gerado ainda não inclui operações guided — web usa `client.raw`.

## Débitos
- Regenerar OpenAPI + `@qmind/api-client` quando o contrato estabilizar.
- `show_when` no catálogo ainda não é avaliado (todas as perguntas atuais são incondicionais).
- Evidência anexada no Wizard não cria `evidence_links` tipados para a pergunta guided (só IDs na resposta).
- Cláusulas 6–10 e IA fora do escopo desta entrega.

## Ops
- Publish deve ler sessão/respostas **antes** de `conn.commit()` (GUC `app.organization_id` é local à transação).
- Script de publish: não truncar `VITE_COGNITO_CLIENT_ID` com sed agressivo; sync com `COGNITO_APP_CLIENT_ID` + strip `\r`.
