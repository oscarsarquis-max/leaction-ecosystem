# Revisão do proprietário — Panne Demo 026

Achados da revisão humana da demo. Não inicia CURSOR-027.

## Estado consolidado

| ID | Estado |
|---|---|
| R026-001 | **validada** |
| R026-002 | **validada** |
| R026-003 | **validada** |
| R026-004 | **validada integralmente** |
| R026-005 | **validada** |
| R026-006 | **validada integralmente** |
| R026-007 | **validada integralmente** |
| R026-008 | **validada integralmente** |
| R026-009 | **validada integralmente pelo Cortex** |
| R026-010 | **validada integralmente pelo Cortex** |
| R026-011 | **validada integralmente pelo Cortex** |
| R026-012 | **corrigida e revalidada (ciclo técnico + confirmação Cortex da instância)** |

## R026-001 — tela `/organizacao` vazia após login

| Campo | Valor |
|---|---|
| Identificador | `R026-001` |
| Estado | **validada** (Cortex no navegador) |

---

## R026-002 — Quadro + troca de org

| Campo | Valor |
|---|---|
| Identificador | `R026-002` |
| Estado | **validada** (integralmente pelo Cortex no navegador; Panne → Horizonte → Panne) |

---

## R026-003 — Lista `/ordens` legível + percurso

| Campo | Valor |
|---|---|
| Identificador | `R026-003` |
| Estado | **validada** (integralmente pelo Cortex no navegador) |

---

## R026-004 — Linguagem humana e divulgação progressiva

| Campo | Valor |
|---|---|
| Identificador | `R026-004` |
| Estado | **validada integralmente pelo Cortex no navegador** |

### Validação Cortex (navegador)

Confirmados:

- isolamento Panne → Horizonte → Panne;
- limpeza imediata dos dados na troca;
- linguagem humana no perfil de aplicabilidade;
- `Sim`, `Não` e `Não informado`;
- `Varejo`;
- `Sólido`;
- `Lactose — evidência insuficiente`;
- `50 g`;
- plural e totais do estoque;
- ausência de `true`, `false`, `retail`, `solid` e `Código técnico não catalogado` na superfície principal.

### Correção (resumo)

- Booleanos anuláveis → Sim / Não / Não informado (sem converter ausência em Não)
- Enums → catálogos centralizados; desconhecido → `Opção ainda não catalogada`
- `lactose` → `Lactose — evidência insuficiente`
- Evidência: `documentacao/evidencias/cursor-026/revisao-proprietario/R026-004-perfil-humano.md`

### Documentos

- Decisão: [LINGUAGEM-HUMANA-E-DIVULGACAO-TECNICA.md](../decisoes/LINGUAGEM-HUMANA-E-DIVULGACAO-TECNICA.md)
- Inventário: [INVENTARIO-LINGUAGEM-TECNICA-026.md](INVENTARIO-LINGUAGEM-TECNICA-026.md)

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.

---

## R026-005 — Cabeçalho da caixa de acesso

| Campo | Valor |
|---|---|
| Identificador | `R026-005` |
| Estado | **validada pelo Cortex no navegador** |

### Sintoma

Em `/entrar`, a marca aparecia como placa/retângulo sobre o fundo creme da caixa — hierarquia superior confusa e retângulos sobrepostos.

### Direção aprovada pelo proprietário

Logo como cabeçalho de ponta a ponta da caixa de acesso; corpo de autenticação abaixo; sem segunda placa atrás da marca.

### Validação Cortex (navegador)

Confirmados: cabeçalho integrado de ponta a ponta; sem placa sobreposta; logo nítida e proporcional; cantos superiores recortados; corpo com espaçamento independente; hierarquia marca/autenticação; desktop e estreito; margens externas; sem rolagem horizontal; ajuda sem romper composição; formulário preservado. Ativo `horizontal-claro.png` coerente com a intenção (sem cabeçalho marrom pesado).

### Composição

| | Antes | Depois |
|---|---|---|
| Estrutura | `img.login-brand` solta no padding da caixa | `header.login-center__header` + `div.login-center__body` |
| Largura da marca | limitada com margem | 100% do cabeçalho (borda 1 px da caixa) |
| Cantos | padding afastava a imagem | `overflow: hidden` na caixa recorta o topo |

### Ativo reutilizado

`images/aprovados/horizontal-claro.png` (sem redesenho). Avaliado `horizontal-escuro.png` (fundo grafite); mantido o claro por contraste com o creme da caixa e continuidade com o arquivo já usado na página.

### Responsividade / a11y

Desktop, estreito, mobile, texto maior; sem rolagem horizontal induzida. `alt="Panne"`; cabeçalho sem foco; formulário intacto.

### Testes

`login-editorial.test.tsx` (inclui asserção estrutural R026-005) + suite de autenticação/entrada afetada.

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-005-*.png` e `R026-005-cabecalho-login.md`.

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.

## R026-006 — Lista e detalhe de planejamento compreensíveis e acessíveis

| Campo | Valor |
|---|---|
| Identificador | `R026-006` |
| Estado | **validada integralmente pelo Cortex** |

### Sintoma

Em `/planejamento`, a tabela mostrava só Código / Data / Turno / Estado. Navegação dependia de `onClick` na linha (`td` sem link, sem ação `Detalhe`, sem descoberta por teclado/leitor). O interlocutor precisava interpretar códigos `PLN-…`. No detalhe, a coluna `Prioridade` exibia só `50`, sem escala nem significado. A ordem da lista seguia `created_at` e parecia não cronológica.

### Validação Cortex (navegador)

Confirmados:

- coluna `Conteúdo` com nomes operacionais dos produtos;
- código público e ação `Detalhe` como links semânticos reais;
- navegação não depende exclusivamente do clique na linha;
- lista ordenada por data operacional, turno e código;
- `PLN-20260824-0004` aberto pelo link acessível;
- detalhe: `Pão francês (Demo)`, `PAO-FR`, `Massa`, `3.300 g`;
- prioridade como `Ordem de processamento`, escala relativa 1–99 (padrão 50), sem Alta/Média/Baixa;
- Panne → Horizonte limpa imediatamente; Horizonte com `Recurso não encontrado`, sem dados da Panne;
- Horizonte → Panne recarrega o plano correto; retorno à lista preserva conteúdo e ordenação.

### Causa

1. Contrato de listagem (`GET …/production/plans`) serializava só o cabeçalho do plano (`plan_out`), sem itens/produtos.
2. UI copiava o padrão antigo de linha clicável, sem `<a>` real (diferente de `/ordens`).
3. `priority` no domínio é inteiro **1–99** (padrão **50**), sem faixas Alta/Média/Baixa; a superfície mostrava o número cru.
4. Ordenação da API era `created_at, id`, não a data operacional.

### Contrato antes / depois

| | Antes | Depois |
|---|---|---|
| Listagem | `id`, `public_code`, data, turno, status, … | + `item_count`, `items_summary` |
| Ordenação | `created_at`, `id` | `operational_date` → turno (`morning`/`afternoon`/`night`) → `public_code` → `id` |
| Cursor | `created_at\|id` | `operational_date\|shift\|public_code\|id` |
| Detalhe | itens + produto (já ok) | superfície de prioridade explicada (sem mudar payload) |

### Decisão de resumo operacional

Uma query em lote (`production_plan_id IN (…)`) com outer join em produto — **sem N+1**.

- 0 itens → `Nenhum item planejado`
- 1 item com nome → nome do produto
- 1 item sem nome → `1 item planejado`
- N itens com ao menos um nome → `{primeiro por sort_order} e mais {N-1}`
- N itens sem nomes → `{N} itens planejados`

Não inventa “produto principal” em multi-item: o primeiro nome segue `sort_order`, não prioridade.

### Significado de prioridade

Campo do **item** (e da ordem): inteiro **1–99**, default **50** (`ValidationError` fora da faixa). Sem faixas canônicas no contrato. Superfície: coluna **Ordem de processamento** com texto `50 · relativa (1–99; padrão 50)` + ajuda contextual. Não rotular Alta/Média/Baixa.

### Regra de ordenação

Ascendente determinística: data operacional → rank do turno → código público → id. Cursor alinhado a essa chave.

### Acessibilidade

Código público como `<Link>`; ação textual `Detalhe`; foco visível (`:focus-visible`); navegação por teclado e “abrir em nova aba”. Clique na linha permanece como conveniência secundária (não é a única forma).

### Isolamento

Lista limpa ao trocar `organization_id` (padrão R026-004). Detalhe via `useAsyncResource` com `orgId` nas deps. Testes Panne → Horizonte → Panne na lista e no detalhe.

### Testes

- Backend: `tests/test_plan_list_r026_006.py` + asserções em `test_production_api.py`
- Frontend: `plans-list-r026-006.test.tsx` (+ isolamento existente do detalhe)

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-006-*.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001 a R026-005 não reabertas.

## R026-007 — Lista e detalhe de receitas operacionais

| Campo | Valor |
|---|---|
| Identificador | `R026-007` |
| Estado | **validada integralmente pelo Cortex** |

### Validação Cortex (navegador)

Confirmados:

- lista com coluna `Situação`; estados humanos e coerentes; ausência de `active` na superfície;
- `F-PAO-FR` aberto corretamente;
- ingredientes por nome e código; farinha 1.000 g; água 650 g; sal 20 g; fermento 15 g;
- percentuais 100%, 65%, 2% e 1,5%; farinha-base Sim/Não; total de farinha 1.000 g;
- fator de escala com precisão operacional; massa-base 1.685 g; massa total alvo 3.300 g; campo de massa total em gramas;
- rendimento, peso por unidade e perda ausentes como “não informado”;
- ensaio `TR-PAO-OK` como `Concluído`; sem `trial concluído` nem decimais de persistência na superfície;
- Panne → Horizonte limpa imediatamente; Horizonte com `Recurso não encontrado`, sem dados da Panne;
- Horizonte → Panne recarrega a receita correta.

### Sintomas

1. Lista `/receitas`: coluna `Identidade` exibia enum cru `active`; filtros já usavam português.
2. Detalhe `F-PAO-FR` / `Pão francês (Demo)`: tabela `Componentes` sem nome/código do ingrediente.
3. Quantidades com precisão de persistência (`1000.000000`) e sem unidade.
4. Escala com fator/massa-base crus (`1.9584569733`, `1685.000000`).
5. Ensaio: `trial concluído`.
6. Rendimento ausente: `— unidades de — g, perda —.`.

### Causas

- Lista usava `versionLabel()` sem mapa para `Formulation.status=active`.
- Dossiê da versão serializava só `ingredient_version_id` + quantidades; ficha já enriquecia label com N+1.
- UI não aplicava formatadores R026-004.
- Rótulos de ensaio misturavam inglês (`trial`).

### Contrato componentes antes / depois

| | Antes | Depois |
|---|---|---|
| Item | ids + quantidades + `%` | + `ingredient{id,code,display_name,version_*}` + `unit{code,symbol,dimension}` |
| Hidratação | inexistente no dossiê | lote org-scoped (`load_item_enrichments`) |
| Outra org / ausente | — | `ingredient: null` → UI `Ingrediente indisponível` |

### Correspondência real `F-PAO-FR` (API demo)

| Seq. | Ingrediente | Código | Líquido | Farinha-base |
|---|---|---|---|---|
| 1 | Farinha de trigo tipo 1 (Demo) | FAR-TRIGO | 1000 g | sim |
| 2 | Água (Demo) | AGUA | 650 g | não |
| 3 | Sal refinado (Demo) | SAL | 20 g | não |
| 4 | Fermento biológico fresco (Demo) | FER-BIO | 15 g | não |

Unidade confirmada: `measurement_unit.code = g` (dimensão massa obrigatória na formulação).

### JOIN / batch

Após `items_of`: uma query de `IngredientVersion` (org), uma de `Ingredient` (org), uma de `MeasurementUnit`. Sem N+1. Ficha técnica reutiliza o mesmo helper.

### Linguagem dos estados

| Domínio | Valores | Rótulos |
|---|---|---|
| Identidade | `development`, `active`, `retired` | Em desenvolvimento, Ativa, Aposentada |
| Versão | `draft`, `published`, `retired` | Rascunho, Publicada, Aposentada |
| Ensaio | `planned`, `in_progress`, `completed`, `cancelled` | Pendente, Em andamento, Concluído, Cancelado |
| Aprovação | `submitted`, `approved`, `rejected`, `revoked` | Em revisão, Aprovado, Rejeitado, Revogado |

Coluna da lista: **Situação** (não Identidade).

### Precisão operacional

`formatOperationalQuantity` (g), `formatBakersPercentage`, `formatScaleFactor` (até 4 casas úteis). Valores integrais só em auditoria técnica.

### Escala

Texto: fator multiplica a receita-base para a massa total; massa-base = soma líquida; campo `Massa total (g)`.

### Rendimento

Ausência → frases separadas (`Rendimento não informado` / `Peso por unidade não informado` / `Perda não informada`). Perda 0–1 → percentual. Sem zero inventado.

### Isolamento

Lista e detalhe limpam em troca de `organization_id`. Horizonte: 0 receitas; sem vazamento de `F-PAO-FR`. Enriquecimento exige `organization_id`.

### Testes

- Backend: `test_recipe_item_enrichment_r026_007.py` + asserções em `test_recipe_http.py` (4 passed)
- Frontend: `recipes-r026-007.test.tsx` + `recipes.test.tsx` (11 passed)

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-007-receitas.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001 a R026-006 não reabertas.

## R026-008 — Lista e detalhe de ingredientes compreensíveis

| Campo | Valor |
|---|---|
| Identificador | `R026-008` |
| Estado | **validada integralmente pelo Cortex no navegador** |

### Validação Cortex (navegador — 2ª passagem)

Confirmados:

- lista com links no nome e no código; ação explícita `Detalhe`;
- estados e filtros em linguagem humana; tipo `Simples`;
- nenhum alerta de consulta substituída;
- Proteína: 10 g por 100 g · Medido; Carboidrato: 70 g por 100 g · Medido; Gorduras totais: 2 g por 100 g · Medido; Sódio: 0,4 g por 100 g · Medido;
- Glúten · Contém · Fonte sintética de demonstração;
- nenhuma fonte global disponível;
- SKU-FAR-25; embalagem 25 kg; fornecedor Moinho Demo; último valor R$ 13,00;
- origem interna ausente da superfície principal;
- Panne → Horizonte limpa imediatamente; Horizonte com recurso não encontrado, sem dados da Panne;
- Horizonte → Panne restaura nutriente, alergênico, embalagem, fornecedor e preço.

### Histórico de validação

| Passagem | Resultado |
|---|---|
| 1ª | **não validada** — lista/estados/cancelamento ok; detalhe falhou (nutrição/alergênico/embalagem) porque o **processo antigo da API permaneceu na porta 5080** (`start-demo` não reinicia se `/health` já responde) |
| 2ª | **validada integralmente pelo Cortex no navegador** — após encerramento completo e reinício confirmado da demo |

### Sintomas da 1ª passagem (já corrigidos e confirmados no navegador)

Lista com links/`Detalhe`; estados humanos; filtros; tipo; cancelamento invisível; `Medido`/`Contém`; fontes pluralizadas; origem técnica fora da superfície.

### Sintomas bloqueantes (Cortex, após reinício informado)

No detalhe `FAR-TRIGO`:

- `Nutriente indisponível: … · Medido` (4 linhas) — nomes ausentes;
- `Alergênico indisponível · Contém · …` — Glúten ausente;
- `Embalagem: 25.000` sem unidade;
- `Último valor: R$ 13,00` divergente do retorno documental `R$ 13,10`.

### Causa exata (2ª passagem)

1. **Nutriente/alergênico/unidade indisponíveis na UI:** o processo uvicorn em `:5080` **ainda rodava o binário/código antigo** (sem campos `nutrient`/`allergen`/`unit`/`supplier` no JSON). `start-demo.ps1` **não reinicia** se `/health` já responde — após a 1ª passagem o FE novo lia payload velho. Banco e JOIN de catálogo estavam corretos (Proteína/Glúten existem).
2. **Embalagem sem unidade:** mesmo processo antigo (sem `unit` no item) + seed incoerente `package_quantity=25000` com `kg` (= 25 t). Intenção do SKU `FAR-25`: **saco de 25 kg**.
3. **Preço R$ 13,00:** verdade operacional — `latest_price` por `observed_at` aponta para lançamento de recebimento `13.0000 BRL` (mais recente que o seed `13.10`). Não é bug de formatação.

### Natureza dos catálogos

| Catálogo | Escopo | RLS | Enriquecimento |
|---|---|---|---|
| `nutrient_definition` | **global** | usuário autenticado | lote por `id`, sem `organization_id` |
| `allergen` | **global** | usuário autenticado | lote por `id`, sem `organization_id` |
| `measurement_unit` | **global** | usuário autenticado | lote por `id` |
| `supplier` / `supplier_item` | **organizacional** | org | unidade global + fornecedor filtrado por org |

### Payload ao vivo (relevante, sem tokens)

**Antes (API antiga em `:5080`):** nutrientes só com `nutrient_id`/`value`/`value_status`; alergênico só com `allergen_id`/`presence`; item sem `unit`/`supplier`; `package_quantity=25000`; `latest_purchase.unit_price=13.0000`.

**Depois (API reiniciada + seed):**

- nutrientes com `nutrient.name` Proteína/Carboidrato/Gorduras totais/Sódio + `unit.symbol=g`;
- alergênico com `allergen.name=Glúten`;
- item `package_quantity=25`, `unit.code=kg`, `supplier.display_name=Moinho Demo`, preço `13.0000 BRL`.

### Verdade final da embalagem

`SKU-FAR-25` → **25 kg** (`package_quantity=25`, `measurement_unit=kg`). Seed corrigido e item existente em `panne_demo` sincronizado.

### Verdade final do preço

**Último valor = R$ 13,00** (API/banco/UI). Seed mantém histórico 12,50 e 13,10; o mais recente é o recebimento 13,00.

### Correção (2ª passagem)

- Encerrar forçadamente listeners `:5080`/`:5180` e subir demo de novo (código de enriquecimento carregado).
- Seed: `25` + `kg`; update idempotente do item existente.
- Documentação alinhada à evidência.
- Teste de órfão defensivo mantido.

### Testes

- Backend: `test_ingredient_enrichment_r026_008.py` + `test_ingredient_http.py` (**4 passed**)
- Frontend: `ingredients-r026-008.test.tsx` + `ingredients.test.tsx` (**15 passed**)

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-008-ingredientes.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001 a R026-007 não reabertas.

## R026-009 — Validade, elegibilidade e significado de disponibilidade

| Campo | Valor |
|---|---|
| Identificador | `R026-009` |
| Estado | **validada integralmente pelo Cortex** |

### Passagens

| Passagem | Resultado |
|---|---|
| 1ª | Corrigiu matemática e semântica de saldos/elegibilidade; Cortex validou parcialmente (totais e tabela) |
| 2ª | Corrigiu referência temporal visível e navegação contextual (`?lot=`); Cortex validou a parte visual |
| 3ª | Unificou a data operacional API↔UI (`as_of`); **validação integral** pelo Cortex |

### Validação integral (Cortex)

Confirmado no navegador após a terceira passagem:

- API e UI compartilham a referência operacional (`as_of=2026-08-24` no demo).
- Nota demo e relativos: LOT-000002 · 27/08/2026 · vence em 3 dias; relógio real não substitui a âncora.
- Totais (g): Físico 33.100 · Reservado 24.000 · Não reservado 9.100 · Impedido 2.300 · Disponível para produção 6.800.
- LOT-000003 bloqueado e LOT-000004 quarentena com disponibilidade operacional zero.
- Links de posição com parâmetros distintos; `?lot=LOT-000004` filtra; filtro identificado; **Limpar filtro**.
- Troca Panne → Horizonte remove parâmetro e dados; retorno à Panne restaura o cenário.
- Sem regressão nos totais nem na semântica de elegibilidade.

### Já aprovado (histórico — não reabrir)

- Totais e semântica da 1ª passagem.
- Nota demo, `?lot=`, filtro/limpar/isolamento da 2ª.
- Fonte única `inventory_operational_date()` + contrato `as_of` da 3ª.

### Correção temporal (3ª passagem — referência)

API usava `date.today()`; UI demo usava `VITE_DEMO_ANCHOR_DATE`. Sem `as_of` no JSON.

**Fonte única:** `inventory_operational_date()` em `operational_date.py`.

| Ambiente | Data |
|---|---|
| `PANNE_ENV=demo` | `PANNE_DEMO_ANCHOR_DATE` (default seed `2026-08-24`); relógio real irrelevante; formato inválido → `OperationalDateError` |
| Produção / local / test | Data civil em **America/Sao_Paulo**; âncora demo **ignorada** |

**Contrato:** listagens `/inventory/lots`, `/inventory/balances`, `/inventory/fefo` devolvem:

```json
{ "items": [...], "as_of": "2026-08-24", "timezone": "America/Sao_Paulo" }
```

Cliente comum **não** envia `as_of`. FE usa `resolveInventoryAsOf(body.as_of)`.

**Consistência demo:** `start-demo.ps1` define `PANNE_DEMO_ANCHOR_DATE` e espelha em `VITE_DEMO_ANCHOR_DATE` (quadro ainda usa Vite; estoque usa API).

### Contradição observada (histórico 1ª passagem)

- Validade: LOT-000003 Bloqueado, LOT-000004 Em quarentena.
- Posição/visão geral: saldo não reservado rotulado como **Disponível**, incluindo 1.500 g + 800 g impedidos.
- Totais: Físico 33.100 g · Reservado 24.000 g · “Disponível” 9.100 g (= 6.800 elegíveis + 2.300 impedidos).

### Definições antes / depois

| Conceito | Antes (UI) | Contrato / depois |
|---|---|---|
| `physical_quantity` | Físico | Inalterado — saldo no local |
| `reserved_quantity` | Reservado | Inalterado — comprometido com ordens |
| `available_quantity` | **Disponível** (ambíguo) | Continua `physical − reserved`; UI: **Não reservado** |
| `eligible_quantity` | — | Não reservado **e** elegível (status + validade) → **Disponível para produção** |
| `impeded_quantity` | — | Não reservado inelegível → **Impedido** (⊆ não reservado) |
| `as_of` | implícito / divergente | Metadado explícito da API; mesma ref. em elegibilidade, FEFO, totais e UI |

### Regra de status e validade

Elegível se `status == available` **e** (`expires_on` é null **ou** `expires_on >= as_of`).
Dia do vencimento **ainda é válido** (`< as_of` = vencido).
Bloqueado / quarentena / expired / exhausted / closed → inelegível.
`as_of` = `inventory_operational_date()` (demo: âncora; demais: America/Sao_Paulo).

### Matriz dos seis lotes (seed demo, farinha, g)

| Lote | Status | Validade | Local | Físico | Reservado | Não reserv. | Impedido | Disp. produção | FEFO |
|---|---|---|---|---|---|---|---|---|---|
| LOT-000001 | available | 2026-10-03 | Almox. Central | 20000 | 20000 | 0 | 0 | 0 | não (sem saldo livre) |
| LOT-000002 | available | 2026-08-27 | Almox. Central | 4000 | 4000 | 0 | 0 | 0 | não (sem saldo livre) |
| LOT-000003 | blocked | 2026-09-13 | Almox. Central | 1500 | 0 | 1500 | 1500 | 0 | **não** |
| LOT-000004 | quarantined | 2026-09-08 | Quarentena | 800 | 0 | 800 | 800 | 0 | **não** |
| LOT-000005 | available | 2026-09-23 | Almox. Central | 3800 | 0 | 3800 | 0 | 3800 | sim |
| LOT-000006 | available | 2026-10-08 | Almox. Central | 3000 | 0 | 3000 | 0 | 3000 | sim |

### Reconciliação

- Físico 33.100 = 20k+4k+1,5k+0,8k+3,8k+3k
- Reservado 24.000 = 20k+4k
- Não reservado 9.100
- Impedido 2.300 = 1.500+800
- Disponível para produção 6.800 = 3.800+3.000

### FEFO

Só `status=available`, não vencido segundo o mesmo `as_of`, ordena por `expires_on`, usa saldo não reservado. Exclui 000003/000004. Override: `inventory.expired.override` + flag; reserva nunca usa override.

### Apresentação

- Visão geral / posição / lotes: inalterados visualmente na 3ª passagem.
- Lotes: nota demo e relativos derivados do `as_of` do payload.
- Posição: `?lot=` preservado (sem regressão).

### Isolamento / N+1

Troca de org limpa listas e remove `?lot=` incompatível. Serialização de balances/lots em lote (sem N+1 por linha).

### Testes

- Backend: `test_inventory_eligibility_r026_009.py` — **6 passed** (elegibilidade, âncora demo estável, produção ignora âncora, fuso SP, âncora inválida).
- Frontend: `inventory-r026-009.test.tsx` — **10 passed** (UI usa `as_of` da API mesmo com âncora Vite divergente; filtro/isolamento).

### Evidência de payload (reinício completo)

`GET .../inventory/lots` e `.../balances` em demo: `as_of=2026-08-24`, `timezone=America/Sao_Paulo`; LOT-000002 `expires_on=2026-08-27`, `production_eligible=true`.

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-009-estoque-elegibilidade.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001 a R026-008 não reabertas.

## R026-010 — Continuidade operacional: reservas, movimentos e separação

| Campo | Valor |
|---|---|
| Identificador | `R026-010` |
| Estado | **validada integralmente pelo Cortex** |

### Passagens

| Passagem | Papel |
|---|---|
| 1ª | Enriquecimento de reservas, movimentos e leitura da separação |
| 2ª | Adoção de leitura somente + links por alocação |
| 3ª | Correção final da linguagem da limitação |

### Validação integral (Cortex)

Confirmado no navegador após a terceira passagem:

**Reservas** — ordem pública e link; ingrediente; necessário/reservado/falta; situação; contexto histórico humano; alocações; cada lote com link próprio (`LOT-000002` → `?lot=LOT-000002`, `LOT-000001` → `?lot=LOT-000001`).

**Movimentações** — data/hora; tipo traduzido; item; lote; local; sinais; unidade; documento; origem traduzida; auditoria recolhida; sem códigos crus na superfície.

**Separação** — leitura PICK-000001; ordem e produto; status/data/responsável; ingrediente/quantidade/lote/local; indicação FEFO; conferência humana; impressão; mensagem honesta; seletor e confirmação removidos; sem mutação; sem jargão de API.

**Isolamento** — Panne → Horizonte remove lista e detalhe; Horizonte conforme permissões; sem dados Panne residuais.

### Já aprovado (histórico)

- Semântica e superfícies acima; não reabrir sem necessidade.

### Bloqueios → correções

**1–2 (1ª→2ª).** Ordem confirmada no seletor + botão sem linhas → Alternativa B (leitura somente).

**3.** Link só no primeiro lote → link por alocação.

**4 (2ª→3ª).** Mensagem de limitação expunha `POST /inventory/picks`, `Idempotency-Key`, `status=confirmed`, «backend» e unicidade.
Texto final na superfície:
`Nesta demonstração, você pode consultar e imprimir separações já confirmadas. A preparação de uma nova separação — necessidades, sugestão de lotes, revisão e confirmação — ainda não está disponível nesta tela.`
Contrato técnico (multiplicidade, idempotência, endpoint) permanece só na evidência/documentação.

### Sintomas (histórico 1ª)

- Reservas/movimentos rasos; separação com UUID e `lines: []`.

### Contratos

#### Reservas / adoção / movimentos

Inalterados na 2ª passagem (já aprovados), salvo links por alocação.

#### Separação (após 2ª/3ª)

- Leitura + detalhe + `.pick-print-area` + Imprimir.
- Sem formulário de confirmação; nenhuma chamada mutável pela UI desta tela.
- Mensagem humana (3ª): consulta/impressão disponíveis; preparação de nova separação indisponível nesta tela.
- Isolamento: troca de org limpa listagem e detalhe selecionado.

Contrato técnico (só documentação/evidência): várias picks por ordem possíveis; criação via comando autenticado com chave de idempotência e linhas válidas; status de criação confirmado.

### Matriz demo

| Superfície | Dados |
|---|---|
| Reserva completa | ORD-20260824-0003 · Farinha · 2.500/2.500/0 · LOT-000002 |
| Reserva parcial | 90.000/21.500/68.500 · LOT-000002 (1.500) + LOT-000001 (20.000) |
| 7 movimentos | openings + receipts + supplier_return −200 |
| PICK-000001 | ORD-20260824-0003 · Focaccia (Demo) · 500 g · LOT-000001 · Sugerido |

### N+1 / Permissões

Listagens em lote. Leitura `inventory.read`; confirmação API permanece `inventory.separate` (sem UI neste recorte). Sem preço nestas telas.

### Testes

- Backend: `test_inventory_continuity_r026_010.py` — 3 passed.
- Frontend: `inventory-r026-010.test.tsx` — mensagem humana; scanner sem jargão; leitura/impressão; links; isolamento.

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-010-continuidade-reservas-movimentos-separacao.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001…009 não reabertas.
- Alternativa A (preparação completa de nova separação) não implementada neste ciclo.

---

## R026-011 — Fornecedores, itens comerciais e histórico de preços

| Campo | Valor |
|---|---|
| Identificador | `R026-011` |
| Estado | **validada integralmente pelo Cortex** |

### Passagens

| Passagem | Resultado |
|---|---|
| 1ª | Código entregue; tentativa Cortex falhou **exclusivamente** por API antiga em `:5080` |
| 2ª | Reinício completo → validação integral no processo novo |

### Validação integral (Cortex)

Confirmado no navegador após reinício da demo:

- fornecedores com links semânticos e ação Detalhe;
- estados humanos; contagem real de itens;
- Moinho Demo · **1 item ativo**; GET de detalhe ok;
- FOR-MOINHO · SKU-FAR-25 · Farinha de trigo tipo 1 (Demo) · FAR-TRIGO · 25 kg;
- último preço R$ 13,00 · data **24/08/2026, 20:03**;
- histórico (mais recente primeiro): R$ 13,00 · Recebimento; R$ 13,10 · Cadastro de demonstração; R$ 12,50 · Cadastro de demonstração;
- distinção custo operacional ≠ valor contábil;
- nenhuma criação ou alteração executada;
- Panne → Horizonte limpa detalhe e histórico; Horizonte «recurso não encontrado»; sem dado financeiro Panne residual.

### Causa da 1ª falha (não reabrir)

API antiga PID 6616 (14:16:07) sem `active_item_count` e sem `GET /suppliers/{id}` (405). Validação final no processo reiniciado (API 42328 · 15:04:42).

### Correção (2ª)

Somente reinício operacional — **sem mudança funcional de produto**:

1. `stop-demo.ps1` + kill residual `:5180`
2. Portas `5080`/`5180` livres
3. `start-demo.ps1` → API PID **42328** StartTime **15:04:42**; FE PID **53712** StartTime **15:04:43**
4. `/health` e `/ready` ok no processo novo

### Payload ao vivo (após reinício, sem token)

**Lista — Moinho:** `active_item_count: 1` (não zero).

**Detalhe `GET …/suppliers/7a6a4dea-…015e`:** HTTP 200 · Moinho Demo · FOR-MOINHO · Ativo · SKU-FAR-25 · Farinha de trigo tipo 1 (Demo) · FAR-TRIGO · 25 kg · R$ 13,00 · `price_access: true`.

**Histórico:** 13,00 (`is_latest`, receipt, 2026-08-24) → 13,10 (seed, 2026-08-23) → 12,50 (seed, 2026-08-14).

### Contrato — antes → depois (1ª passagem de código)

| Superfície | Antes | Depois |
|---|---|---|
| `GET /suppliers` | id, code, name, status | + `active_item_count` (lote, sem N+1) |
| `GET /suppliers/{id}` | inexistente | fornecedor + itens + `price_access` |
| `GET /items/{id}/prices` | preços crus | org-scoped; gating; `is_latest` |
| Lista / detalhe FE | rasa / inexistente | links + Detalhe + itens + histórico |

### Cadeia real (panne_demo, Moinho)

| Campo | Valor |
|---|---|
| Fornecedor | `FOR-MOINHO` · Moinho Demo · `active` |
| Item | `SKU-FAR-25` · 25 kg |
| Ingrediente | `FAR-TRIGO` · Farinha de trigo tipo 1 (Demo) |
| Último | R$ 13,00 · `2026-08-24T23:03:21Z` · recebimento |
| Histórico | 13,10 · 12,50 |
| IDs (auditoria) | supplier `7a6a4dea-…015e` · item `2e1c8c3b-…694c3` |

### Permissões / ausências / custeio / N+1

Inalterados desde a 1ª passagem (ver evidência).

### Testes

- Backend: `test_suppliers_r026_011.py` — asserts explícitos contra contagem zero e detalhe 405; histórico alinhado ao item.
- Frontend: `suppliers-r026-011.test.tsx`.

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-011-fornecedores-itens-precos.md`

### Fora de escopo

- CURSOR-027 não iniciado.
- Sem commit, push, merge ou deploy.
- R026-001…010 não reabertas.
- Sem valorização contábil; sem formulário de item/preço nesta tela.
- Endurecimento de `start-demo`/`stop-demo` → **R026-012**.

---

## R026-012 — Inicialização e encerramento confiáveis da demo

| Campo | Valor |
|---|---|
| Identificador | `R026-012` |
| Estado | **corrigida e revalidada** — ciclo técnico completo pelo Cursor; instância final confirmada pelo Cortex (`/health` `/ready` `/entrar` 200, `panne_demo`, âncora `2026-08-24`) |

### Motivação / incidentes

| Item | Sintoma |
|---|---|
| R026-003 | FE novo + API antiga |
| R026-008 | API antiga sem enriquecimento |
| R026-011 | API antiga sem contagem / GET detalhe (405) |

Em todos: `/health` ok → `start-demo` reutilizava processo → Cortex via defeito funcional. `stop-demo` só matava PIDs do `pids.json` (launcher), deixando Node/Vite órfão.

### Causa raiz

1. `start-demo` reutilizava se `/health` respondia (sem prova de código/instância).
2. `pids.json` gravava PID do launcher (`npm.cmd` / wrapper), não do listener real.
3. `stop-demo` não matava árvore nem órfãos comprovados nas portas.
4. (bug encontrado nesta correção) PowerShell é case-insensitive: `$ApiHealth` (URL) era sobrescrito por `$apiHealth` (JSON) no loop de wait.

### Antes → depois

| Antes | Depois |
|---|---|
| Reuso implícito por `/health` | Sempre ciclo limpo; `-ReuseExisting` opt-in com `instance_id` |
| PID launcher só | `instance.json`: launcher + server + comando sanitizado + âncora |
| Stop frágil | Prova Panne (path/cmdline sob `C:\Projetos\panne`); órfãos comprovados; desconhecido → aborta sem matar |
| Sem identidade no health | `/health` em `demo` expõe `demo.instance_id`, `logical_database`, `demo_anchor_date`, `process_id` |

### Modelo de processos

- API: launcher python → listener uvicorn na `:5080`
- FE: launcher `npm.cmd` → listener `node`/Vite na `:5180`
- Registro em `.tmp-demo/instance.json` (+ espelho legacy `pids.json`)
- Logs por execução: `api-YYYYMMDD-HHMMSS.{out,err}`, `fe-...`

### Segurança

Não mata processo só por ocupar 5080/5180. Exige prova Panne. Desconhecido: informa PID/comando sanitizado e aborta (exit 2). Sem senhas/tokens no registro.

### Testes

- Backend: `test_demo_health_r026_012.py` + `test_health.py` — 7 passed
- Harness: `scripts/dev/tests/r026-012-lifecycle.ps1` — 14 passed
- Manual: stop → portas livres → start (PIDs novos + instance_id) → start replace → stop → stop idempotente → start final

### Validação

- **Ciclo técnico** (Cursor): stop → portas livres → start → replace → stop → stop idempotente → start final.
- **Cortex**: confirmou a instância final em `/health` 200, `/ready` 200, `/entrar` 200, ambiente demo, banco `panne_demo`, âncora `2026-08-24`. Identificador efêmero da execução registrado só na evidência (não é contrato permanente).
- O Cortex não repetiu pessoalmente todo o harness automatizado; validou o estado final da demo.

### Evidências

`documentacao/evidencias/cursor-026/revisao-proprietario/R026-012-ciclo-demo.md`

### Fora de escopo

- CURSOR-027 não iniciado; sem commit/push/merge/deploy neste registro
- R026-001…011 não reabertas; sem mudança de negócio
