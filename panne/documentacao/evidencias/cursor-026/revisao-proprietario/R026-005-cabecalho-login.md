# Evidência R026-005 — cabeçalho da caixa de acesso

Data: 2026-08-27
Produto: Panne Demo
Estado: **validada pelo Cortex no navegador**
Sem commit / push / CURSOR-027.

## Sintoma

Em `/entrar`, a marca aparecia como retângulo/placa sobre o creme da caixa (`login-brand` com margem interna).

## Direção aprovada

Cabeçalho estrutural de ponta a ponta no topo da caixa; corpo de autenticação abaixo com padding próprio.

## Composição

| | Antes | Depois |
|---|---|---|
| Estrutura | `section.login-center` > `img.login-brand` + conteúdo | `section.login-center` > `header.login-center__header` + `div.login-center__body` |
| Marca | imagem solta com margem | `img.login-center__brand` width 100% no cabeçalho |
| Cantos | padding da caixa afastava a marca | `overflow: hidden` + `padding: 0` na caixa; cantos superiores da caixa recortam o cabeçalho |

## Ativo

`frontend/images/aprovados/horizontal-claro.png` (já usado na página). Fundo do PNG alinhado ao creme do cabeçalho; sem novo desenho.

## Medição (Playwright, desktop 1440)

- `login-center` padding `0`, overflow `hidden`
- imagem: gaps 0 em relação ao header (1 px = borda da caixa)

## Arquivos de evidência

| Arquivo | Conteúdo |
|---|---|
| `R026-005-entrar-desktop.png` | página completa |
| `R026-005-caixa-cabecalho.png` | recorte da caixa |
| `R026-005-entrar-estreito.png` | janela estreita |
| `R026-005-entrar-mobile.png` | 390×844 |
| `R026-005-entrar-texto-maior.png` | texto 125% |
| `R026-005-foco-entrar.png` | foco no botão Entrar |
| `R026-005-ajuda-aberta.png` | ajuda aberta |

## Acessibilidade

- `alt="Panne"` mantido
- cabeçalho sem foco/ação
- formulário e ordem de foco inalterados
- `aria-labelledby="login-heading"` na caixa

## Validação Cortex

Confirmada no navegador: cabeçalho integrado de ponta a ponta; sem placa sobreposta; logo proporcional; cantos corretos; corpo espaçado; hierarquia clara; desktop/estreito; margens; sem rolagem horizontal; ajuda ok; formulário preservado. `horizontal-claro.png` coerente com a intenção do proprietário.
