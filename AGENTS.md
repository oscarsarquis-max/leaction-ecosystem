# AGENTS — monorepo leaction-ecosystem

## Sync de banco Docker entre máquinas (LAN)

Scripts obrigatórios no git / em todo push quando alterados:

| Arquivo | Papel |
|---------|--------|
| `sync-db-from-lan.ps1` | Atalho na raiz (máquina **destino**) |
| `infra/sync-ecosystem-db-from-lan.ps1` | Lógica de compare + dump/restore |
| `infra/open-leaction-db-lan.ps1` | Libera `:5433` na **origem** |

**Regra para o agente:** ao fazer commit/push, nunca deixar esses scripts só locais. Se criar ou alterar utilitários de backup/restore/sync sob `infra/`, incluí-los no mesmo push.

Uso rápido (destino, após `git pull`):

```powershell
cd C:\Projetos
.\sync-db-from-lan.ps1 -SourceHost 192.168.x.x -CompareOnly
.\sync-db-from-lan.ps1 -SourceHost 192.168.x.x -Force
```
