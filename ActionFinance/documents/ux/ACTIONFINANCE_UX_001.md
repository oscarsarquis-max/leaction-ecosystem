# ACTIONFINANCE_UX_001 — Experiência operacional da fatia de títulos

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_UX_001 |
| Versão | 0.6 |
| Status | IMPLEMENTADO no recorte local PRM_006 (acesso); identidade visual PRM_005 e regras 003/004 preservadas |
| Data | 29/09/2026 |
| Dependências | ACTIONFINANCE_PRM_003 §6 e §9; ACTIONFINANCE_PRM_004 §3; ACTIONFINANCE_PRM_005 |

## Mudança de recorte

PRM_003/004 entregaram a operação. **PRM_005 aplica a identidade Action Finance** às mesmas telas: tokens, marca compacta, shell e componentes de apresentação. Sem novas funções financeiras.

## Identidade e tokens

Tokens em `:root` (`frontend/src/app.css`). Não são extraídos da imagem da marca.

| Token | Valor final | Uso |
|---|---|---|
| `--brand-navy` | `#14143D` | Sidebar, entrada, texto sobre ouro |
| `--brand-blue` | `#24219B` | Seleção, links, ação secundária |
| `--brand-blue-hover` | `#1C197E` | Hover das ações azuis |
| `--brand-gold` | `#FFE366` | Ação principal e destaque de marca |
| `--brand-gold-hover` | `#F4D34F` | Hover da ação principal |
| `--canvas` | `#F3F5FB` | Área de trabalho |
| `--surface` | `#FFFFFF` | Tabelas, formulários, diálogos |
| `--text` | `#18243A` | Texto principal |
| `--text-muted` | `#526078` | Texto secundário |
| `--border` | `#818A9C` | Divisórias e controles (ajustado de `#D7DEEA` para contraste de borda ≥3:1 no branco/canvas) |
| `--selection` | `#EAEAFE` | Item selecionado em área clara |
| `--success` | `#166534` | Conclusão comprovada |
| `--warning` | `#854D0E` | Atenção (vencido), fundo claro |
| `--danger` | `#B42318` | Erro e ação crítica |

Ouro com texto navy; nunca texto branco no botão amarelo. Azul profundo com texto branco. Ouro não é estado de vencimento. Vencido usa ⚠ + `warning`. Recebido/pago comprovado usa `success`. Fonte de sistema: Segoe UI, system-ui, sans-serif. Corpo 16 px; auxiliar 14 px; título 26/22 px; resumos 24–28 px; `tabular-nums`. Espaçamento 4/8/12/16/24/32. Raio 8 px (controles) e 12 px (superfícies). Sem fontes remotas, gradientes decorativos ou números animados.

## Marca

Arquivos em `frontend/src/assets/brand/`, importados pelo build:

| Arquivo | Origem compacta | Intrínseco | SHA256 |
|---|---|---|---|
| `actionfinance-yellow.png` | `logoamarelo-previa.png` | 2098 × 749 | `332179CEB05EFB12B6DB5523D631D787319428FF511D5C97776C4A9F5E8BA1EB` |
| `actionfinance-blue.png` | `logoazul-previa.png` | 2127 × 739 | `AE022ADB1D554D8188849EBA1D8674D57B3804E0F2C8A349823AD490D02AC0EC` |
| `actionfinance-white.png` | `logobranco-previa.png` | 1254 × 1254 | `A29779E088E171BCA42D80BE75199E55A1A2688DC53DE177320C1396EB2AF477` |

`BrandLogo`: variante `yellow` no shell e na entrada; `blue` e `white` disponíveis para fundo futuro (branca é quadrada — composição vertical). Alt “Action Finance Capital”. Sem `object-fit: cover`, filtro ou recorte. Exibição com `width` + `height: auto`.

## Componentes

`AppShell`, `BrandLogo`, `PageHeader`, `StatusBadge`, `FinancialSummary`, `CompactRef`, `Modal`. Botões e campos usam as classes globais (`secondary`, `danger`, `link`, `form`). Seletores e o pesquisável são superfície + borda, não botão ouro.

## Shell e rotas

Desktop ≥1024 px: sidebar navy 248 px, logo amarela 212 px, item ativo com faixa ouro + `aria-current`. Topo branco ≥72 px (empresa; Demonstração local; usuário/Sair). Conteúdo padding 24 px, máx. 1440 px.

768–1023: drawer, Menu e logo 144 px na primeira linha; empresa e badge/usuário na segunda, se houver espaço. &lt;768: Menu à esquerda e logo 144 px à direita; empresa na segunda linha; badge e usuário/Sair na terceira, com quebra interna. Backdrop e foco do drawer só com `compact && navOpen`. Escape devolve ao Menu visível; destino efetivado foca `#page-title`; recusa de formulário sujo mantém o contexto. Redimensionar para desktop encerra o drawer sem focar o Menu oculto.

Tabela no desktop ≥1024; cartões abaixo. Nunca ambos visíveis.

| Tela | Caminho |
|---|---|
| Entrada demo | qualquer rota sem sessão |
| Lista a receber | `/receivables` |
| Lista a pagar | `/payables` |
| Novo / editar | `/receivables/new`, `/payables/new`, `.../:id/edit` |
| Detalhe | `/receivables/:id`, `/payables/:id` |
| Registrar recebimento/pagamento | `/receivables/:id/settlements/new`, `/payables/:id/settlements/new` |
| Detalhe da baixa | `/settlements/:id` |
| Contas financeiras | `/financial-accounts`, `/financial-accounts/new`, `/financial-accounts/:id` |
| Cadastros | `/catalogs/counterparties`, `/catalogs/categories` |

Abre em A receber. Navegação: A receber, A pagar, Contas financeiras, Cadastros. Sem dashboard no lugar da lista. Token demo só em memória. Sem “Todas as empresas”. Sem rodapé técnico “Fundação técnica…” nas páginas operacionais.

## Lista, formulário e detalhe

Lista: uma superfície de resumo (restante / vencidos / rascunhos da API); busca sempre visível; demais filtros recolhíveis abaixo de 1024 px, com “Filtros (ativos)” e Limpar. Referência compacta + Copiar (“Referência copiada” em `aria-live`). Situação em badge com texto.

Formulário: superfície 880 px; seções Identificação, Valor e datas, Classificação. Rascunho secundário; Registrar primário. Estorno/cancelamento definitivo em `danger`.

Detalhe: referência, contraparte e situação; faixa Original / Recebido ou Pago / Restante; Registrar ouro só quando permitido; Corrigir secundária; Cancelar título crítica. Baixas em tabela no desktop.

Registrar recebimento/pagamento: aviso de que não envia dinheiro; conta pesquisável; um envio; resultado desconhecido congela a chave.

Estorno: “Nenhuma devolução ou operação bancária será enviada.”; Voltar / Confirmar estorno do registro (`danger`).

Contas: saldo gerencial identificado; rename/inativar em área secundária; extrato com período visível e Saldo anterior / Saldo final do período / Saldo atual. Mobile: Entrada/Saída e Saldo após em linhas distintas.

Controles ≥ 44 px. Sem “Pix enviado”, “Pagamento executado”, logotipo de banco ou “conciliado”.

## Acesso (PRM_006)

Produção (OIDC): marca amarela, base navy, ação **Entrar**. Texto discreto “Acesso restrito a contas autorizadas.” Sem campo de token e sem diagnóstico de fundação. Demo local permanece identificada e só no perfil `local-demo`.

Após login: jornada de Contas a receber. Uma empresa autorizada é selecionada; várias aparecem no seletor por nome; nenhuma autorizada mostra “Seu acesso ainda não foi liberado” com Sair / Tentar outra conta.

Sessão expirada: mensagem clara e Entrar novamente. Falha do provedor: `/?login=failed` sem loop. 403 de revogação não revela dados de outros clientes.

Sair encerra só o ActionFinance (cookie/sessão). A sessão do provedor pode permanecer. Rascunhos não salvos pedem confirmação antes de sair ou trocar de empresa. Escritas com resultado desconhecido não se repetem sozinhas após novo login; a chave só é reenviada se o mesmo ator/empresa ainda estiver na memória da página.

## Fora desta fatia (proposto)

Conciliação bancária, execução de pagamento, transferências entre contas, seletor livre de tenant. Variantes azul/branca da marca em contextos ainda não usados. IdP corporativo real (provisionamento externo).
