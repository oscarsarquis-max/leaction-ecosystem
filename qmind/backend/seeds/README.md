# Seeds — catálogos globais (separados das migrações)

Não misturar dados de cliente/demonstração com catálogos.

| Arquivo | Conteúdo |
|---|---|
| `001_maturity_catalog_v0.sql` | Modelo `qmind_maturity_iso9001` / `0.1.0` (`domain-docs-v0` / `003_Maturity_Model.md`) |
| `002_assessment_model_stub.sql` | Modelo de avaliação stub + ISO 9001:2015 referências autorizadas mínimas |

Aplicar **após** `alembic upgrade head`, como admin:

```powershell
Get-Content seeds\001_maturity_catalog_v0.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind_dev
Get-Content seeds\002_assessment_model_stub.sql -Raw | docker exec -i leaction_db psql -U admin -d qmind_dev
```
