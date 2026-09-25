# Parecer — quantidade e conteúdo por embalagem

Ensaio autenticado, organização descartável **Ensaio itens**. Sem Demo, sem a nota 50661, sem confirmar estoque, sem publicar.

## O que a tela passou a fazer

Uma linha da nota registra **quantidade comprada**, **unidade de compra**, **conteúdo de cada embalagem** e **preço por embalagem**. A conta aparece antes de salvar. **Adicionar outro item** abre produto diferente. Unidade de compra começa vazia (não há `KG` pré-selecionado). O nome fiscal não preenche o conteúdo.

Ordem na linha: 1. o que foi comprado → 2. conteúdo de cada embalagem → conta → 3. ingrediente na Panne. **Cadastrar novo ingrediente** fica ao lado da busca, em ação secundária.

## Provas objetivas

| Caso | Resultado |
|---|---|
| `2 pacotes × 100 g` | Conta `2 pacotes × 100 g = 200 g` e valor da linha R$ 9,00. Persistido: qtd 2, unidade `pacote`, conteúdo 100 g, convertido 200 g. |
| `100 pacotes × 100 g` | Conta `100 pacotes × 100 g = 10 kg` e valor da linha R$ 500,00. Persistido: qtd 100, convertido 10 000 g. |
| Ingrediente existente | Primeira linha associada a Farinha de trigo ensaio, sem POST em `/ingredients`. |
| Ingrediente novo | Segunda linha usa Trigo especial da casa; cadastro só na gravação dos itens. |
| Erro | Salvar sem quantidade/unidade mostra o erro no campo; a descrição digitada permanece. |
| Cancelar | Voltar no diálogo devolve à linha; a descrição permanece. |
| Estoque | `stock_applied=false`, saldos 0. Salvar itens não cria lote nem movimento. |

## Capturas (página inteira)

Desktop 1440 e 390 px, na pasta deste parecer:

- `01-vazio-*` — nota sem itens; **Adicionar item** visível no primeiro viewport em 390
- `02-erro-*` — validação no campo, linha preservada
- `03-dois-pacotes-*` — conta 200 g e preço por pacote
- `04-dialogo-*` — cadastro secundário; em 390, Voltar e Usar cabem no viewport
- `05-cem-pacotes-*` — segunda linha 10 kg + ingrediente novo pendente
- `06-salvo-*` — as duas linhas persistidas, estoque ainda separado

390: largura útil 359 px, padding esquerdo 16 px, sem overflow horizontal. Incorpora o recorte `bbcbd5d`.

## Fora deste recorte

Não publicar. Não confirmar entrada. Melhorias de título da nota e do coach de fluxo ficam para o próximo prompt.
