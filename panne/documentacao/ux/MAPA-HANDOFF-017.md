# Mapa de handoff para o CURSOR-017

Documentado. **Não executar neste ciclo.**

## Reutilizar

`Shell`, `Feedback`, `StatusBadge`, tokens bege/grafite, rota `/producao/ordens/:id/executar`, cliente HTTP, `useCommand`.

## Refatorar

1. Cabeçalho textual “Panne” → logo horizontal (compacto &lt; 980 px).
2. Navegação plana de quatro itens → domínios + trilho da Oficina.
3. `main` com padding curto → palco 8vw + auxiliar do Atelier.
4. Execução: trocar seções empilhadas por `ops-grid`; preservar pin, confirmações e fluxo 1–7.

## Novos

Submenu, palco, gaveta do assistente, badges de qualidade, favicon, rotas futuras de Componentes (somente leitura no primeiro recorte).

## Tokens

Substituir `--panne-fonte` única por chrome vs display. Acrescentar `--raio-conteudo` e largura 8vw.

## Shell incremental

1. Marca no header, sem mudar rotas.
2. Domínios visíveis; itens atuais viram submenu de Produção.
3. Palco Atelier nas páginas de leitura.
4. Modo operacional compatível: mesma máquina de estados, outro layout de página.

## Impacto nas rotas atuais

`/producao`, `/planejamento`, `/ordens`, `/rastreabilidade`, `/executar`, `/fichas` permanecem. Gestão e Receitas não ganham CRUD neste handoff.

## Compatibilidade com o modo operacional

O CURSOR-016 (fluxo, comandos, snapshots, bloqueios) não muda. Só a composição visual da página central.

## Primeiro recorte

Componentes → Ingredientes: lista de leitura + assistente de completude. Sem escrita real até autorização.

## Critérios visuais e funcionais

- marca visível após o login;
- sem “Cadastros”;
- Oficina no cromado;
- Atelier no centro;
- AA, foco, teclado, toque;
- sem ranking nem badge indevido de conformidade;
- backend soberano; sem custos.
