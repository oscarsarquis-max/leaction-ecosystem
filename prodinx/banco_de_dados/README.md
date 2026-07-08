# Base de Dados Prodinx

## Servidor principal: PostgreSQL local (pgAdmin)

O projeto utiliza o **PostgreSQL 18 local** na porta **5432** — o mesmo servidor que vê no pgAdmin.

| Campo | Valor |
|-------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `prodinx` |
| Username | `postgres` |
| Password | `Cmgv6190!@` |

Tabelas principais: `indicadores` (catálogo) e `medicoes` (histórico de ingestão)

### No pgAdmin

1. Ligue-se ao servidor **PostgreSQL 18** (porta 5432)
2. Expanda **Databases → prodinx → Schemas → public → Tables**
3. Consulte a tabela `indicadores`

## Docker (legado — não usar em produção)

O contentor Docker na porta **5435** é legado. O ambiente ativo aponta para o PostgreSQL **local (5432)**.

### Limpar completamente a base Docker

```powershell
cd banco_de_dados
.\limpar_docker.ps1
```

### Limpar duplicados no PostgreSQL local

```powershell
cd servicos
python limpar_base_local.py
```

## Criar/manter schema

```powershell
.\manter.ps1
```

Ou via serviços Python:

```powershell
cd ..\servicos
python -c "from app import init_db; init_db()"
```
