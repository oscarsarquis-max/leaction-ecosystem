# pgAdmin — acesso aos bancos AWS

## Tunéis SSH (duas janelas abertas)

**Terminal 1 — RDS PanelDX (já existente)**
```powershell
ssh -i "C:\Projetos\Chaves\paneldx-bastion-key.pem" -N -L 5434:paneldx-database.czqyam2auctn.us-east-2.rds.amazonaws.com:5432 ec2-user@3.145.51.253
```

**Terminal 2 — Chamelleon + Diário de Obra (EC2)**
```powershell
ssh -i "C:\Projetos\Chaves\paneldx-bastion-key.pem" -N -L 5435:127.0.0.1:5432 ubuntu@18.227.125.118
```

Ou: `.\infra\aws\pgadmin-tunnel.ps1`

## Servidores registrados no pgAdmin

| Nome no pgAdmin | Host | Porta | Database | Usuário |
|-----------------|------|-------|----------|---------|
| RDS_OFICIAL_AWS | 127.0.0.1 | **5434** | LeAction_SysF, etc. | postgres |
| Chamelleon PROD (AWS) | 127.0.0.1 | **5435** | chamelleon | chamelleon |
| Diario de Obra PROD (AWS) | 127.0.0.1 | **5435** | diario-obra | chamelleon |

- **Sem SSH tunnel no pgAdmin** — túnel manual no terminal (igual ao RDS).
- Senha dos dois bancos Chamelleon: mesma do usuário `chamelleon` na EC2 (bootstrap log).
- Re-registrar após reinstalar pgAdmin: `python infra/aws/register-pgadmin-servers.py`
