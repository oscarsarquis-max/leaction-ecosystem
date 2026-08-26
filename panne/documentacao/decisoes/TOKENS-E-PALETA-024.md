# Tokens e paleta — CURSOR-024

Fonte: `panne/frontend/src/styles/tokens.css`.

## Identidade

| Token | Hex | Uso |
|---|---|---|
| `--panne-grafite` | `#323334` | Cabeçalho e chrome estrutural |
| `--panne-bege` | `#E5E4D6` | Base Oficina |
| `--panne-espresso` | `#49352A` | Texto forte e ênfase |
| `--panne-castanho` | `#6B4A3A` | Seleção e andamento |
| `--panne-caramelo` | `#A06F49` | Contorno de seleção, não texto longo |
| `--panne-trigo` | `#C7A878` | Destaque sobre espresso |
| `--panne-creme` | `#F7F2E8` | Superfície Atelier |
| `--panne-areia` | `#D8C9AF` | Bordas e apoio |

## Semântica

| Token | Hex | Significado | Sinal extra |
|---|---|---|---|
| `--panne-oliva` | `#3D5A3A` | Concluído, disponível, confirmado | texto + ícone/badge |
| `--panne-ocre` | `#8A5A12` | Atenção, espera, validade próxima | texto + badge |
| `--panne-terracota` | `#8B3A2A` | Bloqueio, erro, vencido | texto + badge |
| `--panne-grafite-suave` | `#4A4B4C` | Neutro, rascunho, não iniciado | texto |

Caramelo sobre creme fica abaixo de 4,5:1 e **não** é usado como texto de parágrafo. Contraste AA dos pares oficiais está em `frontend/src/styles/contrast.ts`.

## Regras

- Cor nunca é o único sinal.
- Alertas não pintam superfícies inteiras.
- Foco visível em `--panne-foco`.
- Overlay `--panne-overlay` só em máscaras temporárias.
- `prefers-reduced-motion` desliga animação.
