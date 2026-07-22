# Releases — inove4us & Action Hub

## Regras

1. **Versão por produto**, nunca uma versão única do monorepo.
2. Toda promoção a produção exige: bump em `VERSION` + entrada no `CHANGELOG.md` + tag Git + linha no `DEPLOY_LOG.md`.
3. Não usar planilha como fonte da verdade; o Git é a fonte.
4. Confirmar em produção via health (`version` + `git_sha`).

## Tags

| App | Prefixo da tag | Pasta |
|-----|----------------|-------|
| inove4us | `inove4us/vX.Y.Z` | `inove4us/` |
| Action Hub | `actionhub/vX.Y.Z` | `leaction-platform/` |
| MAtivas | `mativas/vX.Y.Z` | `MAtivas/` |

## Fluxo rápido

```powershell
# 1) Edite Unreleased no CHANGELOG do app (o que mudou)
# 2) Corte o release:
cd C:\Projetos
.\infra\release-app.ps1 -App inove4us -Version 1.0.1 -Summary "resumo curto" -Commit -Tag
.\infra\release-app.ps1 -App actionhub -Version 1.0.1 -Summary "resumo curto" -Commit -Tag
.\infra\release-app.ps1 -App mativas -Version 1.0.1 -Summary "resumo curto" -Commit -Tag

# 3) Deploy do artefato (ECS / EC2)
#    MAtivas: cd MAtivas; IMAGE_TAG=1.0.1 ./deploy.sh && ./deploy-remote.sh
# 4) Anote SHA real no DEPLOY_LOG.md e confira /health
# 5) Push (código + tags):
git push origin HEAD
git push origin inove4us/v1.0.1   # ou actionhub/v1.0.1 / mativas/v1.0.1
```

## Variáveis de ambiente (deploy)

| Var | Uso |
|-----|-----|
| `APP_VERSION` | Sobrescreve o arquivo `VERSION` (opcional) |
| `GIT_SHA` | SHA curto do commit implantado (recomendado no CI/deploy) |

Sem `GIT_SHA`, o health tenta ler o arquivo `GIT_SHA` na raiz do app (gerado pelo script com `-WriteSha`).
