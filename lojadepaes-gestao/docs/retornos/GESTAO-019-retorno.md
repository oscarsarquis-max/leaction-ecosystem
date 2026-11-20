# GESTAO-019 — Situação da receita visível e Publicar no rodapé

Base: `feat/gestao-018-rendimento-peso` (`1d96c07a`). Branch: `feat/gestao-019-situacao-receita`. Sem migração (`GESTAO_SEM_BANCO=1`). Sem pull request. Sem login em produção.

## Checklist

1. **Feito.** `git apply --check` do patch `GESTAO-019-situacao-receita.patch` saiu limpo (código 0) e o `git apply` aplicou. Front: `npx vitest run src/pages/situacao019.test.tsx src/pages/receitas015.test.tsx src/pages/receitas017.test.tsx src/pages/receitas018.test.tsx src/pages/Produtos.form.test.tsx` — **21 testes passando**. Backend: `pytest tests/test_situacao_019.py` — **1 passando** (Postgres de teste na porta 55540; a 55440 está na faixa excluída do Windows nesta máquina). O `conftest.py` passou a derivar `HOST_PORT` de `GESTAO_TEST_ADMIN_URL`.

2. **Feito.** Capturas locais com o backend real em `127.0.0.1:8090` e o Vite em `127.0.0.1:5185`. Em `docs/evidence/gestao-019-local/`: `produtos-1280.png`, `produtos-390.png`, `editor-rascunho-1280.png`. A lista mostra Publicada v1, Rascunho e Sem receita; o editor em rascunho mostra o selo ao lado do título e o botão **Publicar versão 1** no rodapé; a barra lateral mostra “1 sem receita publicada”.

3. **Feito.** Imagem `lojadepaes-gestao:019-20261119`. O deploy imprimiu `banco: nada a fazer neste deploy (GESTAO_SEM_BANCO=1)`. Só o `gestao-api` foi recriado e ficou healthy (anterior: `018-20261112`). `https://gestao.lojadepaes.com.br/` responde 200 e serve `index-CkafZfLf.js`, SHA-256 `bd89e800c1190da6ee3f20ef3acdd144d96f49f1ed069ae7e0b06b25851023f4`, o mesmo do build da imagem. `/api/v1/health` e `/api/v1/ready` respondem 200. `https://lojadepaes.com.br` responde 200. A porta 22 deste ciclo foi fechada (`regras_22` 0). Continuam no ar: `gestao-api`, `infra-api-1`, `lepain`, `infra-caddy-1`, `infra-db-1`.

4. **Feito**, no sentido pedido: não entrei na conta de produção. A conferência nos produtos reais fica com o Oscar.

## O que mudou

- **Lista de Produtos:** a coluna Situação usa `receita` da API — Publicada vN; Publicada vN + Rascunho vN+1; Rascunho; Sem receita; nos comprados, Item ligado ou Sem item.
- **Editor:** a situação aparece ao lado do título; o rodapé ganha **Publicar versão N** (se faltar fermento, leva a Revisar); publicada, o rodapé fica sem botões.
- **Painel do produto:** frases “Publicada · versão N”, “Versão N valendo · rascunho da N+1 não publicado” ou “Rascunho, ainda não vale · publique em Revisar”.
- **GET /produtos:** cada produzido com receita traz `{ situacao, versao, publicada, linhas }` em consultas únicas para a lista; comprado ou sem receita: `null`.
- **Barra lateral de Receitas:** o texto passou a “N sem receita publicada” (singular com “1”).

## Deploy

O `scp` direto do tar (~100 MB) falhou várias vezes (IP público flutuando e conexão resetada). O transporte usou o bucket `lojadepaes-gestao-backup`, prefixo temporário `tmp/`, download no host por URL assinada de curta duração e em seguida `remote-deploy.sh` com `GESTAO_SEM_BANCO=1`. O objeto temporário foi apagado após o deploy (`aws s3 rm`). Nenhuma URL assinada nem credencial entra neste retorno.

## Como voltar

No host, `GESTAO_IMAGE=lojadepaes-gestao:018-20261112` em `/opt/lojadepaes-gestao/deploy/.env` e recriar só o `gestao-api`. A imagem 018 segue no host. O banco não mudou de esquema.
