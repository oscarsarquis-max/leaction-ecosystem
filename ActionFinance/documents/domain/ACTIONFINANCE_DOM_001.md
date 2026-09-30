# ACTIONFINANCE_DOM_001 — Linguagem e estados da fatia de títulos

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_DOM_001 |
| Versão | 0.4 |
| Status | IMPLEMENTADO no recorte local PRM_004 |
| Data | 29/09/2026 |
| Dependências | ACTIONFINANCE_PRM_003; ACTIONFINANCE_PRM_004; ACTIONFINANCE_ARQ_001 |

## Mudança de recorte

Recebíveis e UX operacional entram nesta fatia, sem esperar um prompt só de telas. O título é compartilhado com direção RECEIVABLE ou PAYABLE.

## Produto

ActionFinance é um produto financeiro **autônomo e integrável**. Operação manual do recorte implementado não depende de Spider, ActionHub ou Panne. Não é processador de pagamentos.

Dois modos do mesmo produto: autônomo (entrada e gestão locais) e, no futuro, conectado via Spider. Sem forks.

## Vocabulário

| Termo | Significa | Não significa |
|---|---|---|
| Tenant | Organização cliente do produto | Contraparte que paga ou recebe |
| Empresa | Empresa administrada no tenant | Documento fiscal obrigatório no demo |
| Contraparte | Cliente, fornecedor ou ambos | Cadastro ERP completo; tenant |
| Categoria | Natureza gerencial compatível com a direção | Conta contábil legal |
| Título | Compromisso com valor e vencimento | Recebimento, pagamento, saldo ou lucro |
| Baixa | Registro local de recebimento/pagamento já realizado | Envio de Pix, transferência ou execução bancária |
| Movimento | Entrada/saída gerencial na conta financeira | Extrato conciliado com banco |
| Estorno do registro | Registro adicional que desfaz o efeito da baixa no controle | Devolução de dinheiro ou apagamento do original |
| Conta financeira | Conta gerencial local (banco/caixa/outra) | Conta bancária autenticada ou conector |
| Saldo gerencial | Soma dos movimentos locais, inclusive abertura | Saldo conciliado ou autorizado |
| A receber / A pagar | Direção do título na UI; no resumo, restante pendente | Liquidação executada |
| Origem MANUAL | Entrada local digitada | Dado sincronizado de Hub/Panne |
| Demonstração local | Identificação de ambiente/dado fictício | Conceito de domínio MANUAL_DEMO |
| Referência informativa | Texto opcional do fato simulado | Chave canônica externa |
| Vencido | OPEN, restante positivo e vencimento anterior à data de negócio | OPEN quitado; estado persistido |

Venda não é recebimento. Compra/entrada de estoque não é pagamento. Plano de subscrição não é uma única conta a receber. Soma de títulos não é saldo bancário, receita realizada, lucro ou caixa.

## Máquina de estados

```text
→ DRAFT (criar / editar)
DRAFT --confirmar--> OPEN
→ OPEN (registrar atômico)
OPEN --corrigir com motivo--> OPEN
DRAFT|OPEN --cancelar com motivo--> CANCELLED
```

Cancelado é somente leitura. Sem exclusão física e sem reabertura.

Situação financeira **derivada** (sem coluna persistida de saldo):

```text
DRAFT|CANCELLED → NOT_APPLICABLE
OPEN e realizado = 0 → UNSETTLED
OPEN e 0 < realizado < principal → PARTIAL
OPEN e restante = 0 → SETTLED
```

Realizado = soma das alocações cujas baixas não têm reversão. Restante = principal − realizado. UI: “Em aberto”, “Parcialmente recebido/pago”, “Recebido/Pago”.

```text
OPEN --registrar baixa (parcial ou total)--> OPEN (UNSETTLED|PARTIAL|SETTLED)
baixa --estornar registro--> OPEN (realizado reduzido; movimento inverso)
OPEN com realizado líquido > 0 --cancelar--> recusado
OPEN com realizado líquido = 0 --cancelar--> CANCELLED
```

Após qualquer baixa histórica, mesmo estornada: não alterar principal, moeda, direção, contraparte nem competência. Descrição, vencimento e categoria continuam corrigíveis com motivo.

## Autorização

Permissões: `titles:read/write`, `catalogs:read/write`, `financial-accounts:read/write`, `settlements:read/write/reverse`, além de `system:read` e `company-context:read`. Operador demo recebe escrita deste recorte; consulta só leitura. Ator e papel não vêm do corpo HTTP.

## Fora desta fatia (proposto)

Integração Spider, conciliação bancária, pagamentos externos, baixas em lote, transferências entre contas, juros/descontos/multas/tarifas/impostos/câmbio, recebimento acima do título, distribuição de uma baixa entre vários títulos, IAM de produto.
