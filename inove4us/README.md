# inove4us — Mesa do Inovador (autônomo)

Top of Funnel freemium em **inove4us.com.br**.  
Oficina do Inovador (cópia operacional do PanelDX) + gate de acesso por e-mail/código.

> O código do PanelDX não é alterado. Fontes em `source-from-paneldx/`.

## Stack

- **Frontend:** React + Vite (login) + Oficina EJS/Flask
- **Backend:** Flask + Gunicorn (produção)
- **Banco:** PostgreSQL `inove4us` no Docker `leaction_db` (`localhost:5433`, user `admin`) — mesmas credenciais do PanelDX, banco separado. Bootstrap: `infra/scripts/bootstrap-inove4us-db.ps1`


## Dev local

```powershell
# (opcional) popular DB inove4us a partir do snapshot LeAction_SysF — não altera o PanelDX
cd C:\Projetos\inove4us
.\infra\scripts\bootstrap-inove4us-db.ps1

# API
cd C:\Projetos\inove4us\backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py

# UI
cd C:\Projetos\inove4us\frontend
npm install
npm run dev
```

- Login: http://localhost:5174/acesso  
- Oficina: http://localhost:5174/inovador/?id_clie=…  

## Produção / AWS

Ver roteiro completo: [`infra/DEPLOY.md`](infra/DEPLOY.md)

- `Dockerfile` + `docker-compose.yml`
- Terraform ECS Fargate + ALB + Route 53 + regra SG no RDS
- Scripts: `infra/scripts/build-and-push.ps1`
