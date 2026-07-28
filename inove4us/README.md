# inove4us — Mesa do Inovador (autônomo)

Top of Funnel freemium em **inove4us.com.br**.  
Oficina do Inovador (cópia operacional do PanelDX) + gate de acesso por e-mail/código.

> O código do PanelDX não é alterado. Fontes em `source-from-paneldx/`.

## Stack

- **Frontend:** React + Vite (login) + Oficina EJS/Flask
- **Backend:** Flask + Gunicorn (produção)
- **Banco:** PostgreSQL `inove4us` no Docker `leaction_db` (`localhost:5433`, user `admin`) — mesmas credenciais do PanelDX, banco separado. Bootstrap: `infra/scripts/bootstrap-inove4us-db.ps1`


## Dev local

**Regra:** ao subir o inove4us, o Action Hub (gateway `:4001`, marketplace `:4012`, FE `:4000`) sobe junto.

```powershell
cd C:\Projetos\leaction-ecosystem\inove4us
.\scripts\dev\start-inove.ps1
```

Isso chama `leaction-platform\scripts\dev\start-hub.ps1` e sobe API (`:5011`) + FE (`:5174`).

Manual (equivalente):

```powershell
# 1) Hub
cd C:\Projetos\leaction-ecosystem\leaction-platform
.\scripts\dev\start-hub.ps1

# 2) API
cd C:\Projetos\leaction-ecosystem\inove4us\backend
.\.venv\Scripts\Activate.ps1
python app.py

# 3) UI
cd ..\frontend
npm run dev
```

- Login: http://localhost:5174/acesso  
- Oficina: http://localhost:5174/inovador/?id_clie=…  
 

## Produção / AWS

Ver roteiro completo: [`infra/DEPLOY.md`](infra/DEPLOY.md)

- `Dockerfile` + `docker-compose.yml`
- Terraform ECS Fargate + ALB + Route 53 + regra SG no RDS
- Scripts: `infra/scripts/build-and-push.ps1`
