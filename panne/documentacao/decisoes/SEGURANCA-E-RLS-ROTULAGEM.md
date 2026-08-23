# Segurança e RLS — rotulagem

Permissões distintas: `labeling.read`, `labeling.dossier.create`, `labeling.evaluate`, `labeling.candidate.edit`, `labeling.review`, `labeling.render`, `labeling.invalidate`, `regulatory.source.read`. Sem permissão genérica de certificação. Cognito groups e `legacy_role_label` não autorizam.

Tabelas em `LABELING_TABLES` com ENABLE + FORCE RLS, política org, default deny, runtime sem fallback administrativo.
