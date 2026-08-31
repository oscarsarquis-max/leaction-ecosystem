# Impressões operacionais e gerenciais

**Ciclo:** CURSOR-028-A.  
**Hoje:** fichas HTML + `window.print` + `print.css` (ordem, receita, rotulagem, picks). Sem motor PDF dedicado.

## Princípio

Três **contratos** distintos — não três “temas CSS” do mesmo payload com valores escondidos no cliente.

| Contrato | Audiência | Valores financeiros |
|---|---|---|
| Cozinha | Operador / padeiro | **Proibidos** |
| Gestão | Gestor / owner | Obrigatórios quando houver permissão |
| Rotulagem | Conformidade / expedição | Sem preço; dados legais/produto |

Gate: permissão no **servidor** ao emitir o documento. Cliente não é fonte de verdade para omitir custo.

---

## 1. Cozinha (operacional)

### Conteúdo obrigatório

- Identificação da ordem (código, data, estabelecimento).
- Produto (nome, código) — se houver.
- Receita e **versão**.
- Quantidade planejada / unidades.
- Ingredientes e quantidades; indicação de **lotes** sugeridos/reservados quando houver.
- Sub-receitas e dependências.
- Etapas, tempos, temperaturas, equipamentos.
- Conferências / checkpoints.
- Perdas / tolerâncias operacionais (quantidade, não R$).
- Resultado esperado (rendimento).

### Proibido

- Custo, markup, margem, preço, valor de NF, indicadores financeiros.

### Origem de reuso

Ficha de ordem / execução atual — **filtrar** campos financeiros no serializer `kitchen`.

---

## 2. Gestão

### Conteúdo obrigatório

- Planejado versus realizado (qty, tempo, rendimento, perdas).
- Custo (previsto e real, bases: batelada / kg / unidade).
- Markup aplicado e origem da regra (produto / família / org).
- Margem bruta / contribuição (vocabulário 021).
- Preço calculado / praticado.
- Quantidades e histórico relevante da ordem/receita.
- Links ou IDs para drill-down (ordem → consumos → lotes → recebimentos).

### Origem de reuso

Relatórios de costing/pricing + ficha enriquecida — serializer `management`.

---

## 3. Rotulagem

### Conteúdo obrigatório

- Composição **efetivamente produzida** (não só a receita planejada, quando houver apontamento).
- Alergênicos.
- Informação nutricional (quando disponível).
- Lote do produto acabado.
- Validade.
- Conteúdo líquido / peso.
- Versão da receita / fórmula usada.
- Identificação do produto e estabelecimento.

### Proibido

- Preço e custos (salvo exigência legal futura explícita).

### Origem de reuso

Módulo de rotulagem existente (HTML conferência) — alinhar a FG real quando 028-G/C existirem.

---

## Contratos de API (proposta)

```
GET /prints/orders/{id}?profile=kitchen|management
GET /prints/recipes/{versionId}?profile=kitchen|management
GET /prints/labels/{finishedGoodId|orderId}
```

- `403` se `management` sem permissão de custo/preço.
- `kitchen` nunca inclui chaves monetárias (schema distinto).
- Auditoria: quem imprimiu, quando, profile.

## Critérios de aceite

1. Mesma ordem gera dois HTML distintos; inspeção do DOM/JSON kitchen sem campos de preço/custo.
2. Gestão com permissão vê planejado×realizado e memória de cálculo resumida.
3. Rótulo traz lote/validade/versão/alergênicos.
4. `print.css` continua ocultando chrome; banner demo não vaza para papel (já tratado no ciclo demo).
