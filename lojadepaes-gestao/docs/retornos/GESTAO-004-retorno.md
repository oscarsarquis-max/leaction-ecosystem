# GESTAO-004 — Ajustes antes do lançamento do estoque

Data: 2026-11-02 · Base: `feat/gestao-003-entradas` (`4cc0f1c9`) · Branch: `feat/gestao-004-ajustes`
Produção: imagem `lojadepaes-gestao:004-20261102` em https://gestao.lojadepaes.com.br · `https://lojadepaes.com.br/` responde **200**.

## 1. O que mudou

### Entrada sem nota: tabela densa a partir de 1024 px
- Cada item é **uma linha da tabela**, na ordem do colar da planilha: item · ingrediente · marca · qtd · unidade · conteúdo · lote · validade (com a caixa “sem validade” ao lado) · custo · ⋯.
- Com 20 linhas, a página de 1280 px tem **1.743 px** (cada linha tem 48 px). Antes, cartões de ~330 px: 50 itens passavam de 16 mil px.
- **Cabeçalho fixo** ao rolar. Em 1280 px ou mais a tabela cabe e quem rola é a página; entre 1024 e 1279 px a tabela rola dentro do cartão (para baixo e para os lados) com o cabeçalho fixo dentro dele.
- **Avisos dentro da linha**: “Ingrediente/Item parecido…” e as pendências (ex.: “Falta a validade”) ficam numa **sublinha** da própria linha, só quando existem. Linha sem aviso não ganha sublinha.
- **Teclado**: Tab segue a ordem das colunas (o campo de data do Chrome tem uma parada por pedaço: dia, mês, ano). **Enter na última coluna (custo)** vai para o item da linha de baixo (cria a linha se não houver).
- **⋯**: *Duplicar* (a cópia entra logo abaixo, sem o código do lote, que não se repete) e *Remover*.
- **“Colar da planilha”** no cabeçalho da página: abre um painel com a área de colagem (as linhas entram na tela para conferir, nada é gravado). A dica continua embaixo. O Ctrl+V direto na página continua valendo.
- **Celular (até 959 px) continua como estava**: lista compacta. Entre 960 e 1023 px continua o layout de duas linhas por item de antes (a tabela começa em 1024).

### Rodapé coerente
- Mostra **“N sem validade”** além de itens, a decidir, incompletos e total. O caso “0 incompletos” com duas linhas dizendo “Falta a validade” acabou.
- **Clicar** em “a decidir”, “incompletos” ou “sem validade” leva à primeira linha nessa situação (foco e rolagem na coluna que resolve: o ingrediente/item parecido, a coluna do erro, a validade). No celular abre a linha.
- A frase ao lado do **Gravar entrada** diz o que impede (“Para gravar: decida 1 parecido e complete 2 linhas incompletas.”) ou o que vai ficar pendente (“Pode gravar. A entrada fica pendente: 1 item sem validade.”).

### Ingredientes
- **Aviso de parecidos.** “Farinha de trigo” e “Farinha trigo” passam a mostrar o aviso “N pares parecem o mesmo ingrediente · Juntar”. A regra de “parecido” é a mesma da entrada (`sao_parecidos`, 0,85). **Causa do aviso não aparecer:** quem escolhia “Criar novo” (na entrada) ou “Confirmar novo” (ao criar o ingrediente) gravava junto a decisão “são diferentes”, e o aviso escondia o par para sempre. Agora **“Criar novo” só cria**; o par continua apontado até alguém **Juntar** ou marcar **“São diferentes”** (que é a decisão que esconde o par). Mudança de comportamento no backend: `criar_ingrediente` e `lancar_entrada` deixam de gravar `parecidos_distintos` para ingredientes (para itens continua igual). Pares já decididos em produção continuam decididos; não há migração.
- **Ingrediente sem item**: “nenhum item” no lugar de “0 itens · 0 lotes”, com o selo “Sem saldo” mantido. (Com itens e sem lote: “1 item · nenhum lote”.)

### Detalhes
- A trilha do topo mostrava “Hoje / Hoje”. Telas de primeiro nível (Hoje, Entradas, Ingredientes, Locais, Usuários) mostram **só o título**. Telas de segundo nível mostram de onde vieram (“Entradas / Entrada sem nota”). O celular continua mostrando o nome da seção no botão.

## 2. Testes (só os da área)

| Onde | Resultado |
|---|---|
| Backend `tests/test_estoque.py` (Postgres local descartável) | **26 passed**. Atualizados: o par continua apontado depois de “Criar novo”; “São diferentes” tira o par (e repetir o clique não duplica); ingrediente criado com `confirmar_novo` continua apontado. |
| Frontend Vitest (7 arquivos) | **51 passed** (eram 40). Novos: tabela e cabeçalhos na ordem; Tab/Enter; parecido e pendência na sublinha; rodapé (contagem de validade, contadores que levam à linha, frases); “a decidir” leva ao ingrediente parecido; painel “Colar da planilha”; ⋯ duplicar/remover; celular sem tabela; “nenhum item”; trilha só com o título (unidade e App). |
| `tsc --noEmit`, `eslint`, `vite build` | sem erros |

Nenhum teste rodou contra a produção. O Postgres local de teste (`gestao_test_pg`) foi removido ao final.

## 3. Capturas locais (`docs/evidence/gestao-004-local/`, ambiente local, nada gravado)

Dados: 20 linhas coladas pelo painel, uma com ingrediente parecido (“Farinha de trig” ≈ “Farinha de trigo”), uma sem validade. Rodapé: *20 itens · 1 a decidir · 0 incompletos · 1 sem validade · Total R$ 2.661,90*.

| Captura | O que mostra |
|---|---|
| `entrada-sem-nota-1280.png` | Entrada sem nota, 1280 px, 20 linhas, a parecida (sublinha) e a sem validade |
| `entrada-sem-nota-390.png` | A mesma tela, 390 px (lista compacta) |
| `ingredientes-1280.png`, `ingredientes-390.png` | Ingredientes com o aviso de parecidos; “Sal” com “nenhum item” e “Sem saldo” |
| `entrada-sem-nota-rolada-1280.png` / `-1024.png` | Cabeçalho fixo depois de rolar |
| `entrada-sem-nota-contador-validade-1280.png`, `-contador-decidir-1280.png` | O contador do rodapé levou o foco à linha 13 (validade) e à linha 7 (ingrediente parecido) |
| `entrada-sem-nota-menu-linha-1280.png` | Menu ⋯ aberto |
| `entrada-sem-nota-1024/1440/960/768/320.png` | A tela nas outras larguras |
| `hoje-1280.png`, `hoje-1024.png` | Trilha do topo só com “Hoje” |

`capturas.md` na mesma pasta traz as checagens automáticas (script `scripts/capture-gestao-004.mjs`): sem rolagem horizontal da página e controles com 40 px (44 px no celular) em 320, 390, 768, 960, 1024, 1280 e 1440; cabeçalho fixo; Tab; Enter; contadores; trilha.

Limites que vale saber:
- **1024 a 1279 px**: com a barra lateral (248 px) sobram ~710 px; a tabela precisa de ~900 px, então rola para os lados dentro do cartão (o foco rola sozinho até o campo). A página em si não rola para os lados. A tabela cabe inteira a partir de 1280 px.
- **960 a 1023 px** ainda usa o layout antigo de duas linhas por item (página de ~5.500 px com 20 linhas). Fora do pedido (a tabela começa em 1024); se quiserem, é só baixar o ponto de corte e apertar mais as colunas.
- Na tabela, a unidade “embalagem” aparece como “emb.”, e o custo como “R$/kg”, “R$/L” ou “R$/emb.” (o nome completo continua no rótulo para leitor de tela).

## 4. Publicação (procedimento do 002)

- Autorizado e feito: abrir a porta 22 **só para o meu IP /32**, enviar a imagem, `deploy/remote-deploy.sh`, e fechar **só essa regra**. Migração: `alembic upgrade head` rodou e **não havia migração nova** (sem mudança de esquema). Nada mais foi tocado no servidor (Loja, Caddy, backup, DNS ficaram como estavam).
- Antes: gate de recursos — 909 MB disponíveis, 22 GB livres.
- Depois: `gestao-api` com a imagem `004-20261102`, `healthy`; `/api/v1/health` e `/api/v1/ready` 200; o JavaScript servido em produção é o mesmo arquivo do build local (`index-Zar4vn9w.js`); `https://lojadepaes.com.br/` **200**.
- A primeira execução do script de envio parou no meio (meu script tratou a saída do `alembic` como erro e derrubou a sessão SSH). Rodei de novo, a troca é idempotente: nenhum dado alterado, resultado final acima.
- **Sem dados de teste em produção**: nenhuma entrada, ingrediente ou usuário foi criado; as capturas são todas do ambiente local.
- A regra do meu IP foi fechada; as 29 regras antigas da porta 22 seguem como estavam. A pasta da minha chave foi removida; não mexi nas pastas `loja-ssh-p96-*` de outras sessões.
- O servidor guarda `/opt/lojadepaes-gestao/images/gestao-004.tar` (69 MB) além do `gestao-003.tar`.

## 5. Rollback

1. **Voltar a imagem:** no host, `GESTAO_IMAGE=lojadepaes-gestao:003-20261102` em `/opt/lojadepaes-gestao/deploy/.env` e `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --force-recreate gestao-api` (a imagem 003 ainda está no host; o banco não mudou).
2. **Só o comportamento dos parecidos:** reverter `backend/app/domain/ingredientes.py` e `entradas.py` (as duas chamadas que gravavam `parecidos_distintos` para ingredientes).
3. **Parar só a Gestão:** `deploy/rollback.sh`. A Loja não é afetada.

## 6. Para decidir

- **“Criar novo” deixou de valer como “são diferentes”.** Se preferirem que a escolha de uma pessoa na entrada esconda o par para sempre (como era), é só reverter o item 2 do rollback; o custo é o aviso não aparecer para o caso “Farinha trigo”.
