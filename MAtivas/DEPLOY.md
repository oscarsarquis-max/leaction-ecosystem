# Deploy — MAtivas (produção)

Site: https://metodologiasinovativas.com.br  
Infra: EC2 + ECR (`mativas-backend` / `mativas-frontend`) + RDS (`MAtivas`)

## Checklist obrigatório a cada promoção

1. **Código** — `VERSION` / `CHANGELOG` / tag `mativas/vX.Y.Z` + imagens ECR + `deploy-remote.sh`
2. **Schema** — rodar migrações novas (`apply_00N.py` no container backend)
3. **Dados de domínio** — se mudou conteúdo de tabelas de referência **ou** a biblioteca de passos, sincronizar (abaixo)
4. **Health** — `https://metodologiasinovativas.com.br/health` (`version` + `git_sha` + `db`)

## O que é “domínio” neste projeto

| Artefato | Onde vive | Como sobe |
|----------|-----------|-----------|
| Passos canônicos Faça Fácil | `database/biblioteca_passos.json` (arquivo) | Embutido na **imagem Docker** do backend/worker |
| Catálogo da árvore / match | tabela `problema_mativa` | Sync de snapshot → RDS |
| Textos / labels UI | tabela `ui_content` | Sync de snapshot → RDS |
| Vocabulário | tabela `vocabulary_rules` | Sync de snapshot → RDS |

> Roteiros, professores, desafios e histórico **não** são domínio — não truncar em produção.

## Sync das tabelas de domínio (local → prod)

Na máquina com Docker `leaction_db` populado:

```powershell
cd C:\Projetos\MAtivas
python scripts\export_domain_snapshot.py domain_snapshot.json

scp -i chaves\mativas-key.pem domain_snapshot.json scripts\sync_domain_to_prod.py ubuntu@3.141.12.134:/tmp/
ssh -i chaves\mativas-key.pem ubuntu@3.141.12.134 @"
sudo docker cp /tmp/domain_snapshot.json mativas_prod_backend:/tmp/domain_snapshot.json
sudo docker cp /tmp/sync_domain_to_prod.py mativas_prod_backend:/tmp/sync_domain_to_prod.py
sudo docker exec -e PYTHONPATH=/app -w /app mativas_prod_backend python /tmp/sync_domain_to_prod.py /tmp/domain_snapshot.json
"@
```

## Imagens + containers

```bash
cd MAtivas
IMAGE_TAG=$(tr -d '[:space:]' < VERSION) ./deploy.sh
./deploy-remote.sh
```

## Pós-deploy v1.0.0 (2026-07-22)

- Migration `007` (`curtido_em`) aplicada
- `biblioteca_passos.json` na imagem (51 chaves)
- Domínio sync: `problema_mativa` (39), `ui_content` (20), `vocabulary_rules` (4)
