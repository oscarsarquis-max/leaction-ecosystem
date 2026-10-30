# Desenvolvimento — Loja de Pães

Instruções para Windows (PowerShell). Caminhos a partir de `C:\Projetos\lojadepaes`.

## Primeira vez

1. Copie os exemplos de ambiente (`backend/.env.example` → `backend/.env`, `frontend/.env.example` → `frontend/.env`).
2. Crie o venv e instale a API: `pip install -e ".[dev]"` em `backend/`.
3. `npm install` em `frontend/`.
4. Suba o Postgres **ou** ajuste `LOJADEPAES_DATABASE_URL`.

## PostgreSQL

O Compose em `database/docker-compose.yml` usa o projeto Docker `lojadepaes` (não o nome da pasta `database`, para não colidir com o Phanton).


```powershell
cd C:\Projetos\lojadepaes\database
docker compose up -d
docker compose ps
```

Não use `-v` destrutivo nem `down -v` — o volume `lojadepaes_pgdata` deve permanecer.

PostgreSQL já instalado na máquina: crie um banco **novo** chamado `lojadepaes` e um usuário dedicado. Exemplo (ajuste host/porta/superuser):

```powershell
psql -h 127.0.0.1 -p 5432 -U postgres -c "CREATE USER lojadepaes WITH PASSWORD 'lojadepaes_dev';"
psql -h 127.0.0.1 -p 5432 -U postgres -c "CREATE DATABASE lojadepaes OWNER lojadepaes;"
```

Depois aponte `LOJADEPAES_DATABASE_URL` para esse banco. Não recrie nem limpe bancos de outras aplicações.

## Migrações

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
cd ..\database
$env:PYTHONPATH = (Resolve-Path ..\backend).Path
alembic current
alembic upgrade head
alembic revision --autogenerate -m "descricao"   # só quando houver modelos
```

Detalhes em `database/README.md`.

## API

```powershell
cd C:\Projetos\lojadepaes\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 5075
```

Health não exige banco. Ready exige PostgreSQL; se cair, a resposta é 503 sem URL nem senha.

```powershell
Invoke-RestMethod http://127.0.0.1:5075/api/v1/health
Invoke-RestMethod http://127.0.0.1:5075/api/v1/ready
```

## Frontend

```powershell
cd C:\Projetos\lojadepaes\frontend
npm run dev
```

Abra http://127.0.0.1:5175. O Vite faz proxy de `/api` para `:5075` no modo dev. Prefira `VITE_API_BASE_URL` vazio para o cookie de sessão do admin ficar no mesmo origin.

Gestão: http://127.0.0.1:5175/admin/pedidos e http://127.0.0.1:5175/admin/produtos (exige credencial configurada no backend; ver README).

Fotos de produto: `LOJADEPAES_MEDIA_DIR` (padrão `../var/media` a partir do backend → `lojadepaes/var/media/`). O diretório é criado no primeiro envio, ignorado pelo Git e **precisa entrar no backup**. Não use `frontend/images/` para uploads. Limite: 8 MB; JPEG, PNG e WebP. Arquivos órfãos não são apagados automaticamente nesta versão.

### Responsividade (permanente)

Toda tela da Loja de Pães — vitrine, detalhe, seleção, assistente, mural, biblioteca, login e gestão — precisa funcionar a partir de **320 px** de largura, em tablet, notebook e desktop amplo, inclusive com **ampliação de 200%**. Isso vale para telas futuras, não só para o cabeçalho.

- Layouts fluidos e breakpoints conforme o conteúdo; não criar CSS por modelo de aparelho.
- Sem rolagem horizontal da página, cortes ou sobreposição. Não esconder o problema com `overflow-x: hidden` no documento.
- Não remover informação ou ação essencial em tela estreita: reorganizar (tabelas em cartão, formulários em uma coluna, menu por toque).
- Controles com área de toque confortável (cerca de 44×44 px), menus que abrem e fecham por toque e teclado, foco visível.
- Imagens e o logo oficial (`lojadepaeslogo.png`) mantêm proporção, sem deformar nem recortar o símbolo.
- Estilos: `frontend/src/styles/responsive.css` e `frontend/src/admin/admin.css`.

Conferir larguras 320, 375/390, 768, 1024 e 1440 px, orientação horizontal no celular e os fluxos: vitrine → produto → seleção; assistente; acesso no cabeçalho (Login/Senha); `/admin/produtos` (cadastro/edição); `/admin/pedidos` (lista e detalhe); menus e diálogos por teclado.

## Verificações

```powershell
# backend
ruff check app tests
pytest

# frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Docker

Único Compose desta app: `database/docker-compose.yml` (Postgres 16 + healthcheck + volume). Não há workers em `services/` nesta etapa.

## Manutenção de disco

O disco virtual do Docker (`%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`) cresce com builds e não devolve espaço ao Windows sozinho. Manter a imagem de produção e as três anteriores da cadeia de retorno. Hoje: `lojadepaes:prod-20261030a` (produção), `prod-20261029d`, `prod-20261029c` e `prod-20261029b`.

Imagens antigas da Loja, só tags `lojadepaes:prod-*` fora dessa lista, sem forçar. Se o contêiner ainda usa a imagem, pular:

```powershell
docker image rm lojadepaes:prod-<tag>
```

Cache de build e imagens sem tag. Não usar `-a`:

```powershell
docker builder prune -f
docker image prune -f
```

Compactar o disco virtual numa janela de PowerShell como administrador. O script encerra o Docker Desktop, roda `wsl --shutdown` e usa `Optimize-VHD -Mode Full` se o módulo Hyper-V existir; senão, `diskpart` com `attach vdisk readonly`, `compact vdisk` e `detach vdisk`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Projetos\lojadepaes\scripts\p107c-compact-docker-disk.ps1
```

É proibido apagar volumes. Não rodar `docker volume prune`, `docker volume rm`, `docker system prune` (com ou sem `-a` ou `--volumes`) nem `docker image prune -a`. Não usar Clean, Purge data nem Reset to factory defaults do Docker Desktop.

## Controle de versão

A pasta `C:\Projetos` é compartilhada por vários projetos ao mesmo tempo. Prompt da Loja não troca de ramo na pasta principal: commita só caminhos `lojadepaes/` no ramo que estiver em uso e faz push. Se a Loja precisar de ramo próprio, será em git worktree separado, nunca com checkout na pasta principal.

Todo script de publicação novo apaga o `.tar` local depois do deploy confirmado. Se a publicação falhar, o arquivo permanece para o diagnóstico.

## Protótipo vanilla

Referência preservada em `frontend/prototype/` (`index.html`, `style.css`, `app.js`). A aplicação em desenvolvimento é a árvore React.
