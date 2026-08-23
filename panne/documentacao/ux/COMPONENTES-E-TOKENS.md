# Componentes e tokens

## Tokens da direção aprovada

`--fonte-display`, `--fonte-chrome`, `--fonte-corpo`, `--raio-chrome`, `--raio-conteudo`, `--espaco-conteudo`, além da paleta em `base.css`.

No produto, estes tokens deverão substituir valores soltos de `tokens.css` e de `app.css` — somente após o CURSOR-017.

## Componentes do laboratório

| Peça | Origem | Destino futuro |
|---|---|---|
| Shell grafite + trilho | Oficina | refatorar `Shell` |
| Palco `.stage` + lede | Atelier | páginas de leitura |
| Grade `.cards` / `.ops-grid` | Atelier | início, receita, execução |
| Tabela com faixa | Oficina | quadro |
| Badge + progresso | comum / Oficina | `StatusBadge` |
| Gaveta | Oficina | novo; sem sidebar |
| Pin operacional | Oficina | `ExecutePage` |
| Estados de painel | Atelier no palco | `Feedback` |

## Classificação para o handoff

- **Reutilizar:** `Shell`, `Feedback`, `StatusBadge`, cliente HTTP, `useCommand`, rota `/executar`.
- **Refatorar:** header textual, nav plana, `main` curto, pilha da execução.
- **Novos:** submenu, palco, gaveta, favicon, rotas de Componentes (leitura).
