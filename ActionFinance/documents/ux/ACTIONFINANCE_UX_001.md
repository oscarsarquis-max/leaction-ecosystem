# ACTIONFINANCE_UX_001 — Experiência operacional da fatia de títulos

## Controle

| Campo | Valor |
|---|---|
| Identificador | ACTIONFINANCE_UX_001 |
| Versão | 0.14 |
| Status | Menus em duas barras; sem Mais; faixa #1603AD; aceite não |
| Data | 02/10/2026 |
| Dependências | ACTIONFINANCE_PRM_003 §6 e §9; ACTIONFINANCE_PRM_004 §3; ACTIONFINANCE_PRM_005 |

## Mudança de recorte

PRM_003/004 entregaram a operação. **PRM_005 aplica a identidade Action Finance** às mesmas telas: tokens, marca compacta, shell e componentes de apresentação. Sem novas funções financeiras.

## Identidade e tokens

Tokens em `:root` (`frontend/src/app.css`). Não são extraídos da imagem da marca.

| Token | Valor final | Uso |
|---|---|---|
| `--brand-navy` | `#14143D` | Texto e barra móvel |
| `--brand-mark` | `#1603AD` | Faixa da marca (amostra do `actionfinance-blue.png`) |
| `--brand-blue` | `#24219B` | Seleção, links, ação |
| `--brand-blue-hover` | `#1C197E` | Hover das ações azuis |
| `--brand-gold` | `#FFE366` | Reserva; não preenche botão nem marca |
| `--brand-gold-hover` | `#F4D34F` | Reserva |
| `--canvas` | `#F3F5FB` | Área de trabalho |
| `--surface` | `#FFFFFF` | Tabelas, formulários, diálogos |
| `--text` | `#18243A` | Texto principal |
| `--text-muted` | `#526078` | Texto secundário |
| `--border` | `#818A9C` | Divisórias e controles (ajustado de `#D7DEEA` para contraste de borda ≥3:1 no branco/canvas) |
| `--selection` | `#EAEAFE` | Item selecionado em área clara |
| `--success` | `#166534` | Conclusão comprovada |
| `--warning` | `#854D0E` | Atenção (vencido), fundo claro |
| `--danger` | `#B42318` | Erro e ação crítica |

Ação principal: azul com texto branco. Âmbar (`warning-bg`) só sinaliza pendência, com texto. Ouro não é preenchimento de botão nem de marca. Vencido usa ⚠ + `warning`. Recebido/pago comprovado usa `success`. Fonte de sistema: Segoe UI, system-ui, sans-serif. Corpo 16 px; auxiliar 14 px; título 26/22 px; resumos 24–28 px; `tabular-nums`. Espaçamento 4/8/12/16/24/32. Raio 8 px (controles) e 12 px (superfícies). Sem fontes remotas, gradientes decorativos ou números animados.

## Marca

Arquivos em `frontend/src/assets/brand/`, importados pelo build:

| Arquivo | Origem compacta | Intrínseco | SHA256 |
|---|---|---|---|
| `actionfinance-yellow.png` | `logoamarelo-previa.png` | 2098 × 749 | `332179CEB05EFB12B6DB5523D631D787319428FF511D5C97776C4A9F5E8BA1EB` |
| `actionfinance-blue.png` | `logoazul-previa.png` | 2127 × 739 | `AE022ADB1D554D8188849EBA1D8674D57B3804E0F2C8A349823AD490D02AC0EC` |
| `actionfinance-white.png` | `logobranco-previa.png` | 1254 × 1254 | `A29779E088E171BCA42D80BE75199E55A1A2688DC53DE177320C1396EB2AF477` |

`BrandLogo` variante `blue` (`actionfinance-blue.png`, 2127×739, lettering branco no azul da marca) na faixa do cabeçalho e na barra de entrada. O azul do asset (`#1603AD`) é o fundo da faixa, para as letras aparecerem vazadas, sem placa branca. Largura 200, altura da faixa 56, `object-fit: contain` só para acomodar margem do PNG, sem distorcer. `white` e `yellow` oficiais permanecem no repositório e não são redesenhados. Alt “Action Finance Capital”.

## Componentes

`AppShell`, `BrandLogo`, `PageHeader`, `StatusBadge`, `FinancialSummary`, `CompactRef`, `Modal`. Botões e campos usam as classes globais (`secondary`, `danger`, `link`, `form`). Seletores e o pesquisável são superfície + borda, não botão ouro.

## Shell e rotas

Desktop e mobile: faixa azul da marca (lettering branco vazado, empresa, usuário/Sair) e duas barras no fluxo da página. Principal no branco: Recebimentos, Pagamentos, Contas, Cadastros. Contextual em azul muito claro com os submenus da área. Sem sidebar, sem Mais, sem barra inferior, sem dropdown. Mobile pode abreviar Receber/Pagar e rolar cada barra. Destino efetivado foca `#page-title`; recusa de formulário sujo mantém o contexto. Sem Visão geral vazia.

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
| Recebimentos do Pay | `/pay-receipts`, `/pay-receipts/:id` (homolog e, após V13, PRODUCTION da Loja) |

Abre em A receber. Áreas: Recebimentos (A receber + Transações importadas se o sync Pay estiver visível), Pagamentos (A pagar), Contas (Contas financeiras), Cadastros (Clientes e fornecedores, Categorias). `/catalogs` encaminha a `/catalogs/counterparties`. Ações de criação ficam nas páginas. Pay é sistema integrado da importação, não liquidação. Sem dashboard. Token demo só em memória. Sem “Todas as empresas”. Sem rodapé técnico nas páginas operacionais.

## Lista, formulário e detalhe

Lista: uma superfície de resumo (restante / vencidos / rascunhos da API); busca sempre visível; demais filtros recolhíveis abaixo de 1024 px, com “Filtros (ativos)” e Limpar. Referência compacta + Copiar (“Referência copiada” em `aria-live`). Situação em badge com texto.

Formulário: superfície 880 px; seções Identificação, Valor e datas, Classificação. Rascunho secundário; Registrar primário. Estorno/cancelamento definitivo em `danger`.

Detalhe: referência, contraparte e situação; faixa Original / Recebido ou Pago / Restante; Registrar (azul) só quando permitido; Corrigir secundária; Cancelar título crítica. Baixas em tabela no desktop.

Homologação (`actionfinance.integration.homolog=true` apenas): bloco “Acompanhamento no ActionHub Pay” no detalhe. Faixa **Homologação — sem movimentação real. A consulta não baixa este título.** Mostra **observação financeira** e **última tentativa** em campos distintos (`data-lookup-observation` / `data-lookup-attempt`). **Observada em** usa o carimbo do provedor quando existir; senão **Sem carimbo do provedor** — a UI não inventa horário. **Tentativa em** é o instante local da tentativa. Transporte ou recuperação comunica **Não foi possível atualizar** e conserva a observação anterior. Consulta confirmada **não** é apresentada como baixa do título. Estorno do Pay aparece como “Estornado pelo Pay — sem baixa automática”. Origem SIMULATOR vs ACTIONHUB_PAY identificada. Ação “Consultar no ActionHub Pay” / “Consultar resultado” (tentar novamente). Percurso Spider só em “Detalhes de rastreio”. Produção não mostra o bloco. Sem botão vazio.

Registrar recebimento/pagamento: aviso de que não envia dinheiro; conta pesquisável; um envio; resultado desconhecido congela a chave.

Estorno: “Nenhuma devolução ou operação bancária será enviada.”; Voltar / Confirmar estorno do registro (`danger`).

Contas: saldo gerencial identificado; rename/inativar em área secundária; extrato com período visível e Saldo anterior / Saldo final do período / Saldo atual. Mobile: Entrada/Saída e Saldo após em linhas distintas.

Controles ≥ 44 px. Sem “Pix enviado”, “Pagamento executado”, logotipo de banco ou “conciliado”.

## Acesso (PRM_006)

Produção (OIDC): encaminha direto a `/oauth2/authorization/actionfinance` (Hosted UI clássico do pool Finance). Sem página intermediária exigindo outro clique em Entrar. Falha, logout e expiração mostram **Entrar novamente**. Faixa azul `#1603AD` com lettering branco nas telas locais de espera/erro. Sem campo de token e sem slogan. Demo local permanece identificada e só no perfil `local-demo`. Antes do redirect, o destino interno pedido é gravado em `sessionStorage` e restaurado só se for rota do Finance. Branding nativo clássico (`SetUICustomization`) aplicado só no client `actionfinance-confidential`; reversão em `ops/aws/cognito-hosted-ui/`.

Após login: jornada de Contas a receber. Uma empresa autorizada é selecionada; várias aparecem no seletor por nome; nenhuma autorizada mostra “Seu acesso ainda não foi liberado” com Sair / Tentar outra conta.

Sessão expirada: mensagem clara e Entrar novamente. Falha do provedor: `/?login=failed` sem loop. 403 de revogação não revela dados de outros clientes.

Sair encerra só o ActionFinance (cookie/sessão). A sessão do provedor pode permanecer. Rascunhos não salvos pedem confirmação antes de sair ou trocar de empresa. Escritas com resultado desconhecido não se repetem sozinhas após novo login; a chave só é reenviada se o mesmo ator/empresa ainda estiver na memória da página.

## Recebimentos do Pay (PRM_009)

Área: `/pay-receipts`, acessível em Recebimentos como origem ActionHub Pay — não substitui A receber. Ação **Sincronizar recebimentos** (perfil com `titles:write`). Última execução, consulta atual e pendências atuais em blocos distintos. “Sincronização concluída” não minimiza pendências. Ambiente técnico fica no rastreio, não no corpo (“Empresa autorizada · PRODUCTION” removido).

Lista: origem, referência compacta, contraparte se existir (senão Não informado), atualização na origem, cobrado, pago, situação, pendência. Ausência ≠ zero. Filtros: referência, período (atualização na origem), situação presente, pendência — sobre o conjunto da overview. Sem filtro inerte de estabelecimento/processador/método.

Detalhe de conferência: primeiro nível origem/valores/situação/pendência; segundo nível empresa, datas com semântica, IDs separados; rastreio expansível. Atualizar da origem = sync da empresa. Sem aprovar como real. Histórico só com revisões gravadas. Voltar preserva filtros.

Monitor: jornada satélite com seis fatos reais (solicitação → empresa autorizada → capacidade → provider iniciado → resposta → devolução). Sem painel paralelo. Sem afirmar persistência no AF. RAM 24h / 2000; some no restart.

360 / 768 / 1280 sem overflow (CSS existente + cards). Teclado: botão e links focáveis.

## Fora desta fatia (proposto)

Conciliação bancária, execução de pagamento, transferências entre contas, fluxo de caixa, centros de custo, seletor livre de tenant, busca global de transações, união títulos+Pay. Vínculo automático transação Pay → título. O Hosted UI clássico não replica HTML da prancha: logo centrada acima dos campos; rótulos Username/Password do Cognito.
