# Custos, markup e formação de preços

Ciclo: CURSOR-012. **Descoberta canônica — sem implementação.** Domínio futuro, separado do chão de fábrica.

Custos **não** aparecem ao padeiro por padrão. A permissão `costing.read` não é concedida automaticamente e não entra neste ciclo.

## Previsto versus real

| Camada | Origem | Momento |
|---|---|---|
| Custo previsto | snapshot de materiais da ordem + preços vigentes no domínio de custo + taxas e rateios planejados | na liberação ou em simulação |
| Custo real | eventos de produção (`consumption.recorded`, tempos, perda, descarte, retrabalho, vendável) + preço da fonte usada | após apontamentos |

O chão de fábrica **não** calcula custo. Ele emite eventos que o futuro domínio poderá assinar.

## Componentes (futuros)

- ingredientes (quantidade planejada e consumida);
- embalagens;
- mão de obra (tempo real das etapas, não ranking individual);
- utilidades (energia, água, gás — rateio, não medição obrigatória no piloto);
- perdas e descarte;
- rateios de estabelecimento e de recorte;
- taxas e encargos declarados.

## Bases de expressão

Custo por **batelada**, por **massa** (kg de massa ou produto) e por **unidade vendável**. As três são projeções da mesma memória de cálculo, com unidade explícita.

## Markup e margem

- **Markup** incide sobre o custo (preço = custo × (1 + markup) ou regra equivalente documentada).
- **Margem** incide sobre a venda (margem = (preço − custo) / preço).
- São conceitos distintos. Nenhum dos dois entra na ficha nem no quadro do padeiro.

## Preços

Estados futuros, fora deste ciclo:

- **calculado** — saída da memória de cálculo;
- **sugerido** — calculado com política comercial;
- **aprovado** — decisão humana;
- **praticado** — o que vale no canal/estabelecimento.

`technical_product` não é SKU comercial. Preço praticado vive no domínio comercial/custos.

## Memória de cálculo

Versionada, determinística, sem IA. Guarda algoritmo, versão, precisão, insumos e preços de referência. Mudança de preço ou rendimento gera **nova** memória; não reescreve a antiga. Ordens históricas continuam ligadas ao snapshot de produção, não ao preço vivo.

## Cenários

Simulações por fornecedor, escala, rendimento, canal e estabelecimento. Cenário não altera ordem liberada.

## Permissão

`costing.read` (e futuras `costing.manage` / `pricing.approve`) ficam fora dos papéis de padeiro. Owner/admin ou papel futuro de custos.

## Entradas a partir da produção

Eventos que o custo real poderá consumir, sem o contrário bloquear a ordem neste recorte:

- materiais planejados (snapshot);
- materiais consumidos;
- tempo real;
- uso declarado de equipamento;
- rendimento, perda, descarte, retrabalho;
- quantidade vendável.

Preço e fonte vigentes pertencem ao custo, não à ficha.

## Fora

Estoque, markup na UI de fábrica, formação de preço no CURSOR-012, e qualquer exibição padrão ao `baker_operator`.
