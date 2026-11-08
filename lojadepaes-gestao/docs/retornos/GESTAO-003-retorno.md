# GESTAO-003 — Retorno

Fluxo da padaria (Entradas e Ingredientes), organizações com CNPJ, papéis, interface nova e backup diário.
Publicado em https://gestao.lojadepaes.com.br (imagem `lojadepaes-gestao:003-20261102`), sobre a 002.

Branch `feat/gestao-003-entradas`, a partir de `feat/gestao-002-esqueleto`. Só a pasta `lojadepaes-gestao/` foi alterada.

## 1. Resultado

| Item | Situação |
|---|---|
| Interface (shell 108A, menu do fluxo, logo, ícone da aba) | feito; `docs/PROJETO-INTERFACE.md` |
| Modelo: organização, CNPJ, membros, papéis, `admin_plataforma` | feito, com migração 0002 |
| Entradas, Entrada sem nota, Ingredientes, Hoje | feito |
| Deploy em produção | feito; saudável |
| Backup diário no S3 | feito, com prova |
| Portão de aceite do cliente | feito (1280 e 390) |
| Portão do `oscar` ("Sua conta não opera nenhuma organização") | feito (1280 e 390) |

## 2. Testes

Só os novos desta entrega e os que eles tocam; nada rodou contra a produção.

- **Backend:** 119 passaram (`pytest`), `ruff check` e `ruff format --check` limpos.
  - **Isolamento entre organizações** (`tests/test_organizacoes.py`): com duas organizações, cada uma só enxerga e só grava o que é seu. Vale na API e no ORM (select, agregado e join), e uma gravação entre organizações é recusada.
  - **`admin_plataforma`:** recebe `403 sem_organizacao` em todas as rotas de leitura e de escrita (lançar, ajustar, juntar, locais, ingredientes, entradas, usuários). Cria organização e usuário e redefine senha só por comando no contêiner.
  - Papéis (`dono`, `operador`, `somente_leitura`), escolha de organização no login, CNPJ único e válido (inclui o alfanumérico).
  - Estoque (`tests/test_estoque.py`): entrada atômica e idempotente, saldo derivado do livro, parecido bloqueia até decidir, trigger que impede UPDATE/DELETE em `movimentos`, ajuste por contramovimento, junção, filtros, locais.
- **Frontend:** 40 passaram (Vitest, 6 arquivos), `eslint` e `tsc` limpos, build ok.
  - Casca: nome da organização e CNPJ na barra, menu do fluxo, conta sem organização, escolha entre duas organizações, barra do celular, redirecionamento de rota desconhecida.
  - Entradas (Como chegou? com XML, QR e Digitar "em breve"), Entrada sem nota (parecido bloqueia o Gravar, "Criar novo" libera, grava com a decisão, item existente trava ingrediente e unidade, quem digita não é interrompido) e Ingredientes (lista, painel, ajuste com motivo, juntar).

## 3. Organização e primeiro membro

- **Organização:** "Loja de Pães – Boulangerie", nome curto `boulangerie`, CNPJ **69.423.547/0001-04** (guardado sem máscara), `fonte_loja`, `email_contato` oscar@oscarsarquis.com.br, local padrão "Despensa".
- **Primeiro membro:** `admin@lojadepaes.com.br`, nome de exibição "Loja de Pães", papel `dono`, `email_contato` oscar@oscarsarquis.com.br. A senha foi digitada por Oscar numa janela e não foi gravada em lugar nenhum.
- **`oscar`:** virou `admin_plataforma`, sem organização, com `email_contato` oscar@oscarsarquis.com.br. A senha foi redefinida por Oscar na GESTAO-003A, pelo comando `redefinir-senha`, digitada por ele.
- A Gestão não envia e-mail; a caixa de `admin@lojadepaes.com.br` não existe e nada vai para ela.

## 4. Portão de aceite

| Captura | Conteúdo |
|---|---|
| `docs/evidence/gestao-003/portao-cliente-1280.png` | `admin@lojadepaes.com.br` na produção, barra com "Loja de Pães – Boulangerie · CNPJ 69.423.547/0001-04" |
| `docs/evidence/gestao-003/portao-cliente-390.png` | o mesmo no celular, com o CNPJ na segunda linha, inteiro |
| `docs/evidence/gestao-003/portao-admin-plataforma-1280.png` | `oscar`: "Sua conta não opera nenhuma organização" |
| `docs/evidence/gestao-003/portao-admin-plataforma-390.png` | o mesmo no celular |

O login do `oscar` em produção foi recusado nas tentativas feitas antes da redefinição (3 no total, abaixo do limite de 5 falhas em 15 minutos). Uma primeira tentativa de redefinição terminou com erro e não alterou a senha. Na segunda, o comando terminou com código 0 e o login entrou na primeira tentativa.

## 5. Logo conferida

Original `frontend/images/Loja de Pães logo.png` (2000×2000), versionado sem alteração, SHA-256 `51B1F1616E143A24198F93954FA3CF5457BBBC7C8B7941146486349138914365`. O `scripts/gerar-logos.py` só lê o original.
Derivadas em `frontend/src/assets/` (1202×404): `logo-loja-de-paes.png` e `logo-loja-de-paes-transparente.png`. Sem redesenho, recolorização, distorção nem corte do "RECIPES".

| Onde | Altura medida | Conferência |
|---|---|---|
| Barra lateral (desktop, 960 a 1440 px), leva para Hoje | ~40 px | alt "Loja de Pães"; checagem automática OK nas 3 larguras. Ver `menu-960`, `menu-1280`, `menu-1440` |
| Barra do celular (320, 390 e 768 px) | ~32 px | alt "Loja de Pães"; OK nas 3 larguras. Ver `portao-cliente-390` |
| Gaveta do celular | ~40 px, ao lado de "Gestão" | Ver `menu-320`, `menu-390`, `menu-768` |
| Login (6 larguras, uma a 2x) | ~72 px | alt "Loja de Pães"; OK. Ver `login-*` e `login-1280@2x` |
| Tela "Sua conta não opera nenhuma organização" | ~72 px | Ver `portao-admin-plataforma-*` |
| Aba do navegador | ícone "L" sobre creme, 32 e 180 px | `frontend/public/icone-32.png` e `icone-180.png`, ligados no `index.html`; título "Loja de Pães · Gestão" |

## 6. Backup diário

| Item | Prova |
|---|---|
| Bucket | `lojadepaes-gestao-backup`, us-east-2, privado: bloqueio de acesso público ligado nas 4 opções, SSE-S3 (AES256), expiração em 30 dias (e aborto de upload incompleto em 7) |
| Usuário IAM | `gestao-backup`, política inline só com `s3:PutObject` em `…/*` e `s3:ListBucket` no bucket; nenhuma política anexada |
| Credencial | `/etc/gestao/backup.env`, dono root, modo 600. Não está no repositório nem neste retorno |
| Agenda | `/etc/cron.d/gestao-backup`: `17 6 * * *` (06:17 UTC = 03:17 de Brasília; o servidor está em UTC e o Brasil não tem horário de verão) |
| Script | `deploy/backup-gestao.sh`: `pg_dump -Fc` só do banco `gestao`, confere com `pg_restore --list`, envia pelo `deploy/s3_put.py` (SigV4, só biblioteca padrão, sem AWS CLI no host), guarda 7 dias no host |
| Rodada manual | `gestao-20261102T234050Z.dump`: 43.942 bytes, 0,6 s |
| Objeto no bucket | `gestao/gestao-20261102T234050Z.dump`, 43.942 bytes, AES256 |
| Restauração | arquivo baixado do bucket; `pg_restore --list` leu o índice (118 linhas, 14 tabelas com dados), banco `gestao`, Postgres 16.15 |
| Rollback | apagar `/etc/cron.d/gestao-backup` |

## 7. Deploy

- Imagem `lojadepaes-gestao:003-20261102`, construída com `--provenance=false --sbom=false`.
- Antes da migração, `pg_dump` do banco `gestao` em `/opt/lojadepaes-gestao/backups/gestao-pre003.dump`.
- `deploy/remote-deploy.sh`: migração `0001 → 0002_organizacoes_estoque`, `gestao-api` recriado e saudável. Imagem anterior: `prod-20261102a`.
- `infra-api-1`, `infra-caddy-1` e `infra-db-1` não foram tocados; o Caddy também não (o bloco da Gestão já estava no ar).
- Depois do deploy: `/api/v1/health` 200, `/api/v1/ready` 200, `/entrar` 200, `https://lojadepaes.com.br/` 200, `https://lojadepaes.com.br/admin` 200. Login do cliente e do `oscar` conferidos nas capturas do portão.
- Nenhum dado de teste foi gravado em produção; as telas com dados foram capturadas em ambiente local.
- SSH: aberto só para o IP de Oscar (deploy e backup; depois as tentativas de redefinição da senha do `oscar`). Em cada sessão a regra do próprio IP foi fechada em seguida. Não mexi em nenhuma das outras 29 regras da porta 22, nem nas pastas `loja-ssh-p96-*` de outras sessões; só removi a pasta da minha chave.

## 8. Capturas

**Produção** (`docs/evidence/gestao-003/`, listagem em `capturas.md`):
`login-320`, `login-390`, `login-768`, `login-960`, `login-1280`, `login-1280@2x`, `login-1440`;
`menu-320`, `menu-390`, `menu-768`, `menu-960`, `menu-1280`, `menu-1280@2x`, `menu-1440`;
`portao-cliente-1280`, `portao-cliente-390`, `portao-admin-plataforma-1280`, `portao-admin-plataforma-390`.

**Locais** (`docs/evidence/gestao-003-local/`, banco de revisão descartável com dados fictícios):
as mesmas de login, menu e portão, mais, a 1280 e a 390 px:
`hoje-*`, `entradas-*`, `entradas-como-chegou-*`, `entrada-sem-nota-*` (um ingrediente parecido e uma pendência de validade), `ingredientes-*` e `ingredientes-painel-*`.
Todas passaram na checagem automática de rolagem horizontal e altura dos controles (40 px no desktop, 44 px no celular).

## 9. Correções feitas na revisão visual

- Digitar o nome de um item ou ingrediente que já existe não trava mais o campo no meio da digitação; o reconhecimento acontece ao escolher da lista ou ao sair do campo.
- Um texto de erro solto no rodapé da Entrada sem nota foi corrigido.
- No celular, a primeira linha da Entrada sem nota já abre; o estado "sem validade" aparece na linha.
- Menu lateral: itens com 40 px e o "em breve" ao lado do nome; gaveta com a logo e "Gestão" lado a lado.
- O script de captura agora usa um contexto de navegador novo por captura e não repete o login do admin se ele falhar.

## 10. Rollback

1. **Backup:** `sudo rm /etc/cron.d/gestao-backup`. O bucket e o usuário IAM podem ficar; para desligar de vez, apagar a chave de acesso do `gestao-backup`.
2. **Aplicação:** a imagem 002 (`prod-20261102a`) não funciona com o esquema 0002. Voltar exige, nesta ordem:
   - `alembic -c alembic.ini downgrade 0001_usuarios_sessoes` (apaga organizações, membros e estoque da 003; se já houver dados, restaurar antes o `gestao-pre003.dump` ou o dump mais recente);
   - trocar `GESTAO_IMAGE` em `/opt/lojadepaes-gestao/deploy/.env` para `lojadepaes-gestao:prod-20261102a` e recriar o `gestao-api`.
3. **Parar só a Gestão:** `deploy/rollback.sh` (para o compose e tira o bloco do Caddy). A Loja não é afetada.

## 11. Para saber

- Na porta 22 do Lightsail há 29 regras de IP de sessões antigas; não são desta entrega e ficaram como estavam.
- O servidor guarda `/opt/lojadepaes-gestao/images/gestao-003.tar` (72 MB), para rollback e reuso.
