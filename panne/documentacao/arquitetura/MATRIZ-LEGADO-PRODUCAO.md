# Matriz legado — preservar / repensar / descartar / criar

Ciclo: CURSOR-011. Sem portar DDL. Base: inventários já existentes em `legado/` e os princípios confirmados.

| Tema | Decisão | Motivo |
|---|---|---|
| Imprimir quantidades proporcionais e entregar ao padeiro | **preservar como conhecimento** | Fluxo real e contingência |
| Ficha como único instrumento operacional | **repensar** | Continua existindo, mas deixa de ser a fonte; a ordem o é |
| `tbl_ficha_tecnica` + porção como “ordem” | **descartar** | É receita/escala, sem ciclo de vida de produção |
| Custos e markups na ficha (`PRECO_*`, `VD_*`, `BC_*`) | **descartar do chão** | Domínio de custos separado; padeiro não vê margem |
| `ID_EMPRESA` anulável, sem estabelecimento | **repensar** | Panne exige org + estabelecimento |
| Situação `CADASTRADO`/`CANCELADO` | **repensar** | Máquinas de estado explícitas |
| `tbl_pop*` | **separado** | POP/inspeção, não ordem |
| Vínculo ordem ↔ versão aprovada | **criar** | Ausente no legado inventariado |
| Snapshot das quantidades no momento da liberação/impressão | **criar** | Porção legado é escala editável da ficha, não ordem |
| Planejado ≠ realizado | **criar** | Legado guarda um conjunto de pesos |
| Bateladas | **criar** | Não há estrutura |
| Rastreio de lotes | **criar** | Não há estrutura |
| Eventos de etapa append-only | **criar** | Modo de preparo é texto |
| Fonte única digital/impresso | **criar** | Impressão hoje é derivada da ficha viva |
| Isolamento org/estabelecimento + RLS | **criar** | Legado sem FK e sem RLS |
| Acoplamento ficha–estoque–custo | **descartar** | Não portar |

Mudança posterior na ficha legado altera o que se imprime no dia seguinte sem histórico da ordem antiga. A Panne congela snapshot na liberação (invariantes 3 e 4).
