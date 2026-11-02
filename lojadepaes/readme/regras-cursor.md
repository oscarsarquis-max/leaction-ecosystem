# Regras de trabalho no repositório (Cursor)

Vale para todo prompt da Loja de Pães. Siga sem precisar que o prompt repita.

## Git

- Monorepo `C:\Projetos`. Não troque de ramo, não crie ramo e não use stash.
- Commit só de `lojadepaes/`, no ramo atual. Push normal.
- Proibido: `--force`, `reset --hard`, `rebase`, `clean -fd`, apagar ramos ou refs.
- Nunca commitar: `.env*` (exceto `.env.example`), chaves, tokens, dumps, `.tar`, `.zip`, `node_modules`, `dist`, `.venv` ou arquivo acima de 5 MB.

## Docker

- Proibido: `prune`, `volume rm`, `Purge`, `Reset`.

## Dados

- Sem dado real de cliente em arquivo, teste ou captura.
- Sem ação em pedido real em produção. Em produção, só leitura quando o prompt pedir conferência.
- Regras de estado, avisos e pagamento não mudam sem o prompt pedir.

## Visual

- Siga `readme/backoffice-ui-padrao.md`.

## Verificação

- Testes da área durante o trabalho; a suíte completa uma vez, no fim.
- Capturas só das telas alteradas.

## Publicação

1. Backup.
2. Deploy.
3. Health e ready.
4. Apagar o `.tar` local.
5. Commit e push.
6. Registro em `readme/current-state.md`.
