# CURSOR-033 — Ajustes do Inventário inicial antes do lançamento real

**Resultado:** os seis ajustes estão em produção (API `panne-prod-api:24` + frontend `index-BUXZq1f5.js`). Só mexi na tela `/componentes/estoque/inventario` e no endpoint `POST /inventory/openings/batch`. Sem migração.

- Branch: `feat/panne-033-inventario-ajustes` (a partir de `69255cfb`, o commit publicado do CURSOR-032).
- Commit: `4c33ffdc` (publicado, sem force).
- Tag de produção: `panne-prod-2026-11-02c`.

## O que mudou

| # | Pedido | Como ficou |
|---|---|---|
| 1 | Parecidos | Nome digitado ou colado que não bate exatamente mas é parecido (sem acento/caixa, um contém o outro, ou 1–2 letras de diferença) mostra **"Parecido com: <nome> · [Usar este] [Criar novo]"**. A linha fica **a decidir** e bloqueia a gravação até haver escolha. Digitado: o aviso aparece ao sair do campo (não atrapalha enquanto digita). Colado: aparece na hora. Escolher "Criar" na lista de sugestões já conta como decisão. A API recusa `new_ingredient` com nome **igual** (normalizado: sem acento, caixa e espaços repetidos) a um existente, com a linha certa e o nome que já existe (`ingrediente_ja_existe`). |
| 2 | Custo pela unidade | O rótulo segue a unidade: "R$ por kg", "R$ por g", "R$ por unidade", "R$ por embalagem". A revisão mostra **Valor total do inventário** (quantidade × custo) com "Itens sem custo não somam." |
| 3 | Pendências na hora | Embalagem sem conteúdo é marcada na linha assim que se escolhe "embalagem". O resumo conta "N linhas incompletas" e "N a decidir". "Gravar inventário" fica desabilitado com o **motivo visível** ("Para gravar: …") e o botão "Mostrar o que falta" leva à primeira linha pendente. Linhas coladas e linhas já deixadas mostram o que falta; a linha em que a pessoa está digitando não é marcada antes de sair dela. |
| 4 | Desktop | Títulos na mesma grade e na mesma caixa (borda + preenchimento) da linha. "Duplicar"/"Remover" soltos viraram o menu **"⋯"** por linha (abre com Enter/clique, fecha com Esc e clicando fora). |
| 5 | Celular (390 px) | Lista compacta: uma linha por item (nome, quantidade, unidade, ícone). O ícone é "!" quando há pendência; tocar abre os detalhes (embalagem, validade, lote, custo, menu "⋯"). Resumo, valor total, motivo e "Gravar" ficam num rodapé que acompanha a rolagem. |
| 6 | Litro e ml | Unidades "l (litro)" e "ml" na lista e na colagem (`l`, `lt`, `litros`, `ml`…). Ao escolher, a linha oferece **"Lançar como embalagem de [1] l?"** e o botão **"Lançar como embalagem"** converte a linha (unidade → embalagem, conteúdo = o valor informado, unidade do conteúdo = l ou ml). Enquanto estiver em l/ml a linha não grava. |

Observações de comportamento:

- Rótulos das unidades ficaram curtos ("kg", "g", "unidade", "embalagem", "l (litro)", "ml"); antes era "kg (quilos)".
- O contador "ingredientes novos" não inclui linhas ainda a decidir.
- Sem permissão de criar ingrediente, o parecido só oferece "Usar este".

## Limites que vi e não escondo

- **Rodapé do celular é "sticky"** (acompanha a rolagem). Em página curta (poucas linhas) ele fica logo abaixo da lista, não colado no fim da tela.
- **Nome na lista compacta** mostra uns 12–15 caracteres; "embalagem" no seletor de unidade aparece cortado ("embalage"). O nome completo está no campo (rola) e os detalhes têm tudo.
- **"Parecido" é generoso**: "Sal" é parecido com "Manteiga sem sal" (contém). Custa um clique; preferi isso a deixar passar duplicata.
- **ml**: "Lançar como embalagem" mantém a quantidade como número de embalagens. 3 ml viram 3 embalagens de conteúdo 1 (editável no campo). Não adivinho volume total.
- Alinhamento dos títulos: medi 0 px de diferença entre título e campo no 1440 (no JSON); não guardei medida "antes".

## Testes (só desta tela e deste endpoint)

| Onde | Resultado |
|---|---|
| `backend/tests/test_inventory_opening_batch.py` | **12 passaram** (9 existentes + 3 novos: nome igual com acento/caixa/espaço recusado com contagens intactas; nome só parecido ainda cria; dois nomes novos que só diferem por acento no mesmo lote criam um ingrediente) |
| `src/inventory-batch-031.test.tsx` | 14 passaram (ajustei: menu "⋯", rótulo de custo, botão desligado com motivo) |
| `src/inventory-batch-033.test.tsx` | 20 passaram (parecidos, custo/total, pendências, menu, l/ml, grade do desktop, 390 px) |
| `src/pages/inventoryBatch.test.ts` | 18 passaram |
| `src/pages/inventoryBatch033.test.ts` | 13 passaram |
| `tsc --noEmit`, `eslint` (arquivos tocados), `ruff` (backend), `npm run build` | limpos |

Não rodei a suíte inteira, como pedido.

## Capturas (1440 e 390 px)

Ambiente de captura: organização descartável "Ensaio inventário (descartável)" em Postgres local de teste (`127.0.0.1:55432`), API na porta 5091 e Vite na 5193. Nada de Demo nem Loja. Ao terminar, encerrei **só** os três processos que subi (por PID); nenhum `node` alheio foi tocado.

`panne/documentacao/evidencias/cursor-033/capturas/` (medidas em `capturas-1440-390.json`):

| Arquivo | Mostra |
|---|---|
| `1440-1-parecido-e-incompleta.png` | página inteira: "Açúcar cristalino" e "Manteiga" a decidir, Fermento com embalagem sem conteúdo, Leite em litros com a oferta, e Gravar desligado com o motivo |
| `1440-1c-parecido-detalhe.png`, `1440-1d-incompleta-detalhe.png`, `1440-1f-litro-oferta.png` | recortes das linhas |
| `1440-1e-menu-reticencias.png` | menu "⋯" aberto |
| `1440-2-revisao-com-total.png`, `1440-2b-revisao-detalhe.png` | tudo decidido: **R$ 253,70**, "Itens sem custo não somam." |
| `1440-3-gravado.png` | gravação de verdade na org descartável: 5 itens, 3 ingredientes novos |
| `390-1-parecido-e-incompleta.png` (= `390-1b-rodape-fixo-viewport.png`) | parecido a decidir, linha incompleta com detalhes abertos, rodapé com o motivo |
| `390-1c…`, `390-1d…`, `390-1f…` | recortes |
| `390-2-revisao-com-total.png` | revisão com total e botão no rodapé |

Medidas: estouro horizontal **0 px** em 1440 e 390; menor alvo de toque **44 px** (campos e botões); título × campo no 1440: **0 px** em todas as colunas.

## Deploy (mesmo procedimento do CURSOR-031)

- Imagem `panne/backend` com tags **`4c33ffdc`** e **`prod-4c33ffdc`**, digest `sha256:81a68ae8d8e38472933ab999ed0830d249145c10815190d4929e84cf4f0fd8fa` (buildx `panne-c2`, linux/amd64).
- Novo task definition **`panne-prod-api:24`** a partir do `:23`; conferi por comparação que **só a imagem muda** (`equal=True`). Serviço atualizado; rollout `COMPLETED`, 1 tarefa `RUNNING` com o digest acima.
- `https://api.panne.ia.br/health` → 200 (`ambiente: production`); `https://api.panne.ia.br/ready` → 200; `https://panne.ia.br/` → 200.
- Frontend: build com as variáveis de produção, `assets` com cache longo, `index.html` com no-cache, invalidação CloudFront `E1QFFOL2JO2RBJ` (`I3EUZSOZ23XDV8MG1C8FDWMX7L`) concluída. O site serve `assets/index-BUXZq1f5.js`, que contém os textos novos ("Parecido com", "Mostrar o que falta").
- Tag `panne-prod-2026-11-02c` em `4c33ffdc`, publicada.
- Não fiz gravação de teste em produção (nenhum dado novo na Loja). A recusa de nome igual está provada pelos testes do endpoint e a versão em execução é a do digest acima.

## Rollback

- API: `aws ecs update-service --cluster paneldx-cluster --service panne-prod-api --task-definition panne-prod-api:23 --region us-east-2` (imagem `69255cfb` / `prod-69255cfb`).
- Frontend: o `index.html` anterior (apontava para `index-bhQpKyXa.js`) está em `panne/documentacao/evidencias/cursor-033/index-anterior.html`; para voltar, republicar esse `index.html` com `Cache-Control: no-cache` e invalidar `/index.html` no CloudFront `E1QFFOL2JO2RBJ`. Os assets antigos continuam no bucket.
