# Questões remanescentes após o CURSOR-012

| # | Estado | Nota |
|---|---|---|
| 1 | Limitação preservada | Um papel por associação. Padeiro que planeja precisa de outro papel. |
| 2 | Fechada neste recorte | Liberação só com `production.order.release`. Técnico não libera. Dupla = futuro. |
| 3 | Adiada | Pesagem e atalho `released` → `in_progress` fora deste ciclo. |
| 4 | Fechada no desenho | Pré-fermento = dependência `preferment`. |
| 5 | Parcial | Preparação intermediária = dependência `intermediate`. Insumo `preparation` fica para depois. |
| 6 | Adiada | Capacidade de masseira/forno sem cadastro. |
| 7 | Adiada | Lote e estoque fora. |
| 8 | Adiada | QR/código curto fora. |
| 9 | Adiada | Offline digital fora; ficha continua contingência documental. |
| 10 | Adotada | Relógio do servidor no evento. |
| 11 | Adotada | Um estabelecimento por plano. |
| 12 | Parcial | `production.board.read` existe; sem UI. |

Próximo ciclo (CURSOR-013) não está autorizado por este retorno.
