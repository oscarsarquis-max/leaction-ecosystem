# Auditoria dos logotipos

Arquivos oficiais (intactos):

| Arquivo | Dimensão | Modo | Fundo |
|---|---|---|---|
| `panne/frontend/images/pannebege.png` | 2000×2000 | RGB 24 bit | `#E5E4D6` |
| `panne/frontend/images/pannepreto.png` | 2000×2000 | RGB 24 bit | grafite / uso em ficha |

A assinatura (“panne” + “QUALITY RECIPES” + “@panne.ia.br”) ocupa uma faixa central aproximada de 1300×460 px, começando perto de Y=794. Cerca de **70% da altura é margem sólida**.

## Por que a marca parece pequena ou ausente

1. O ativo é um **quadrado com lettering baixo**. Em 72–120 px de altura o script some.
2. O cabeçalho autenticado **não usa o PNG** — só o texto “Panne”.
3. No login o CSS limita a 22 rem de largura, mas a maior parte do arquivo é fundo, então o script visual fica menor do que o quadro da imagem sugere.
4. Não há versão horizontal oficial, nem favicon, nem símbolo isolado.

Contraste do par bege/grafite ≈ 10:1, adequado a AA/AAA.

Derivados **provisórios** do UX-001 permanecem em `panne/design/ux-001/imagens/`. Ver `TRANSFORMACOES-LOGO.md`.

No UX-002 o proprietário autorizou os derivados digitais. Catálogo rastreável: `panne/design/ux-001/imagens/aprovados/` e [MANUAL-LOGOS-DERIVADOS.md](MANUAL-LOGOS-DERIVADOS.md). Os mestres oficiais continuam intactos e não redesenhados.
