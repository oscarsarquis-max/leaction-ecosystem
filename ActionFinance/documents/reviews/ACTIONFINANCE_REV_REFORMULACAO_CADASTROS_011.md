# ACTIONFINANCE_REV_REFORMULACAO_CADASTROS_011

Identificador: ACTIONFINANCE_REV_REFORMULACAO_CADASTROS_011. Data: 05/10/2026. Relato da reformulação de clientes e fornecedores. Aceite permanece com analista/proprietário. Não é PRM de integração nem renumeração de 009/010.

## Comportamento reproduzido (antes)

`CatalogsPage` apresentava um formulário mínimo na própria lista: campo Nome com `required` HTML + papel + botão **Criar**. Clicar Criar com nome vazio dispara a mensagem nativa do navegador «Preencha este campo». Isso é validação HTML, não falha de gravação. POST `{name,role}` só ocorre depois que o navegador aceita o campo.

A lista não paginava, não buscava documento/fantasia/ID externo e misturava consulta com cadastro. O estado inicial do papel era `BOTH` silencioso. Não havia unidade, endereço, contato, fornecimento, origem nem importação.

## Modelo físico (V14 + V15)

Reaproveita `actionfinance.counterparty` e seus IDs. Enum `role` CUSTOMER/SUPPLIER/BOTH permanece.

| Tabela | Cardinalidade | PK / escopo | Nulabilidade relevante | Índices / histórico |
|---|---|---|---|---|
| counterparty (estendida) | 1 pessoa / empresa | PK id; UNIQUE (tenant,company,id); UNIQUE (tenant,company,code) | name NOT NULL; documento completo ou todos nulos + `document_pending` | UNIQUE parcial do documento quando informado |
| counterparty_unit | 0..n / pessoa | UNIQUE (tenant,company,id); FK composta à pessoa | documento próprio opcional, sem cópia da matriz | UNIQUE parcial do documento da unidade ativa |
| counterparty_address | 0..n / pessoa | FK pessoa; unit_id opcional | campos de endereço nullable; `incomplete` | sem unique de CEP |
| counterparty_contact | 0..n / pessoa | FK pessoa | e-mail/telefone nullable; e-mail não é identidade | — |
| counterparty_supply | 0..n / pessoa | FK pessoa | descrição NOT NULL | não é categoria financeira |
| counterparty_external_identity | 0..n / pessoa | UNIQUE (tenant,company,origin_system,connection_key,external_id) | ID na origem NOT NULL | append-only |
| counterparty_history | 0..n / pessoa | append-only | changes JSONB | INSERT/SELECT |
| counterparty_import_batch / _line | lote 1..n linhas | UNIQUE preview por hash; UNIQUE linha por idempotency_key | raw JSONB no banco, não em log | UPDATE de resultado; gravação **por linha** |

**Matriz/filiais:** uma pessoa jurídica = um `counterparty`. Estabelecimentos são unidades. Documento da filial, se existir, fica na unidade. Unique da pessoa e da unidade são separados. Não se cria segunda pessoa só para filial.

**Backfill:** nenhum documento inventado. Legado permanece `person_kind=UNSPECIFIED`, `document_pending=true`, `origin_kind=MANUAL`.

**Grants:** runtime SELECT/INSERT/UPDATE nos filhos e no lote; INSERT/SELECT em histórico e identidade externa; sem DELETE da contraparte.

## APIs

| Método | Rota | Permissão | Nota |
|---|---|---|---|
| GET | `/api/v1/catalogs/parties` | catalogs:read | Página + `totalItems` do conjunto autorizado |
| GET | `/api/v1/catalogs/parties/{id}` | catalogs:read | Detalhe; documento mascarado sem `catalogs:write` |
| POST | `/api/v1/catalogs/parties` | catalogs:write | Cadastro completo; nome+relação mínimos |
| PUT | `/api/v1/catalogs/parties/{id}` | catalogs:write | Versão obrigatória |
| GET | `/api/v1/catalogs/party-candidates` | catalogs:read | Só a empresa autorizada |
| GET/POST | `/api/v1/catalogs/party-imports` | read template / write preview | Preview **não** grava cadastro |
| POST | `/api/v1/catalogs/party-imports/{id}/confirm` | catalogs:write | Atômico **por linha**; relatório parcial explícito |
| GET | `/api/v1/catalogs/counterparties?compatibleWith=` | catalogs:read | Continua array para o formulário de título |
| POST | `/api/v1/catalogs/counterparties` | catalogs:write | Continua `{name,role}` para «Cadastrar contraparte» |

Documento é texto normalizado (país+tipo+número). CNPJ aceita 14 posições alfanuméricas. Validade sintática ≠ existência fiscal. Sem chamada a Receita, ViaCEP ou Panne.

## Matriz fonte / campo (Panne e pagamentos)

| Fonte observada | Campo real | Propriedade | Destino AF preparado | Situação |
|---|---|---|---|---|
| Panne `supplier` | `display_name`, `code`, `status`, `organization_id` | Panne / organização | `name` / identidade externa `PANNE`+org+id | Sem conector |
| Panne UI de alta | código + nome | Panne | — | Não há campo CNPJ nesta tela |
| Panne fiscal | `emitter_tax_id` no documento, não no cadastro de fornecedor | Panne | documento da pessoa, se um conector futuro autorizar | Não é API de cadastro |
| Arquivo CSV exportado | colunas do modelo | operador | origem FILE | Manual; rótulo «arquivo», não Spider |
| ActionHub Pay | — | Hub | beneficiário futuro ≠ contato ≠ contraparte | Sem campos Pix/banco neste recorte |

Caminho de integração, quando existir: AF → Spider → provider. Finance não acessa o banco Panne.

## Telas

Lista `/catalogs/counterparties`: busca separada; um select de relação (todos/clientes/fornecedores/ambos); situação; identificação pendente; origem; paginação com total do conjunto; Cadastrar abre `/new` sem exigir busca; empty states distintos.

Formulário dedicado (não painel lateral): identificação com checkboxes Cliente/Fornecedor (admite ambos; padrão nunca é Ambos silencioso); unidades; endereço incompleto; contatos; fornecimentos; origem/histórico. Cancelar volta à lista com filtros em `sessionStorage`. Completude por finalidade; texto explícito de que cadastro mínimo não autoriza pagamento.

Importação: arquivo → prévia classificada → confirmação das linhas → relatório. XLSX recusado. Sem botão «Importar do Panne».

Categorias permanecem na jornada mínima anterior.

## Diferenças em relação à prancha

A prancha mistura chips e dropdown de relação e mostra rádios exclusivos Cliente/Fornecedor e uma busca global. O texto do prompt prevaleceu: um só filtro de relação; checkboxes de relação no cadastro; sem busca global fictícia; placeholders não gravados. Duas barras e identidade aprovadas foram preservadas; sem Mais/sidebar.

Inspeção de layout: CSS da lista/formulário reusa `.form`, `.filters`, `.desktop-table`, `.cards` e grade que quebra em 768. 360/1280 herdam o shell vigente. Prova visual autenticada pública desta fatia **não** foi publicada (sem apply produtivo).

## Provas (ambiente controlado)

| Caso | Onde |
|---|---|
| Cadastrar sem preencher busca | `CounterpartiesPages.test.tsx` |
| Empty catalog vs empty search | idem |
| Fornecedor PJ + unidade/endereço; PF sem documento; ambos | `PartyDirectoryIT` |
| Duplicata exata / nome semelhante | idem |
| Concorrência de documento | idem |
| Inativar referenciado; título permanece | idem |
| Viewer sem escrita; isolamento B↛A; total > página | idem |
| Importação prévia sem gravação; parcial; retry | idem |
| POST `{name,role}` e GET `compatibleWith` | idem |
| Documento zeros / CNPJ alfanumérico | `DocumentNumbersTest` |

## Gaps dos conectores

- Não existe API Panne de fornecedor consumível pelo Finance.
- Não existe conector Spider para cadastro Panne.
- Não existe jornada de beneficiário/Pix.
- V13 ainda não está no RDS público; V14/V15 **não** devem ser aplicadas lá sem pacote autorizado.

## Aceite

Implementação local revisável. Aceite do desenho e da publicação: analista/proprietário. Pendências 009/010/PRM_009 permanecem separadas.
