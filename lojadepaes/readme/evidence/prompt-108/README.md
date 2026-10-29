# Prompt 108 — casca do backoffice

29/10/2026. Troca só a estrutura autenticada: menu lateral, barra superior, tokens e componentes base. As telas de antes continuam nos mesmos endereços, com o mesmo miolo. O backend não muda. Alembic continua `d5e9f2a18b33`.

A casca fica em `frontend/src/admin/shell/`. `CatalogTabs.tsx` permanece no repositório e deixa de ser renderizado: os destinos passam para o menu. Gigio não monta quando o caminho começa com `/admin`.

## Rotas

| Caminho | Tela | Item do menu |
|---|---|---|
| `/admin` | home de pedidos | Operação / Pedidos |
| `/admin/pedidos` | fila, resumo e agenda de produção | Operação / Pedidos |
| `/admin/pedidos/{id}` | detalhe do pedido | Operação / Pedidos |
| `/admin/pedidos/solicitacao/{id}` | solicitação de data | Operação / Pedidos |
| `/admin/agenda` | dias, tetos e fechamentos | Produção / Dias, tetos e fechamentos |
| `/admin/produtos` | vitrine e cadastro | Catálogo / Produtos |
| `/admin/produtos/novo` | produto novo | Catálogo / Produtos |
| `/admin/produtos/{id}` | editor | Catálogo / Produtos |
| `/admin/produtos/receitas` | receitas da semana | Catálogo / Receitas da semana |
| `/admin/produtos/receitas/nova` | receita nova | Catálogo / Receitas da semana |
| `/admin/produtos/receitas/{id}` | editor da receita | Catálogo / Receitas da semana |
| `/admin/produtos/gigio` | notas do Gigio | Conteúdo / Gigio |
| `/admin/produtos/gigio/harmonizacoes` | harmonizações | Conteúdo / Harmonizações |
| `/admin/produtos/complementos` | complementos | Conteúdo / Complementos |
| `/admin/fidelidade` | participantes | Clientes / Fidelidade |

“Verificando sessão…” e “Redirecionando…” ficam fora da casca. Parceiros e Repasses aparecem no grupo Marketplace, com selo “em breve”, sem link e fora da tabulação.

## Onde ficou cada capacidade

“Mudou” marca o controle que saiu do cabeçalho antigo ou das abas do catálogo. O endereço da tela não mudou.

| ID | Onde fica agora | Mudou |
|---|---|---|
| T-acesso-01 | vitrine, acesso do cabeçalho, `/#acesso` | não |
| T-acesso-02 | fora da casca, em qualquer `/admin/*` sem sessão | não |
| T-acesso-03 | rodapé do menu, “Notificações neste aparelho” | sim |
| T-acesso-04 | o mesmo painel do rodapé | sim |
| T-acesso-05 | barra superior, conta e sair | sim |
| T-pedidos-01 | Operação / Pedidos, `/admin` e `/admin/pedidos` | não |
| T-pedidos-02 | lentes do resumo, na mesma home | não |
| T-pedidos-03 | agenda de produção, na mesma home | não |
| T-pedidos-04 | busca e paginação da fila, `/admin/pedidos` | não |
| T-pedidos-05 | detalhe, `/admin/pedidos/{id}` | não |
| T-pedidos-06 | aceitar, no detalhe | não |
| T-pedidos-07 | iniciar produção, no detalhe | não |
| T-pedidos-08 | marcar pronto, no detalhe | não |
| T-pedidos-09 | concluir, no detalhe | não |
| T-pedidos-10 | confirmar entrega, no detalhe | não |
| T-pedidos-11 | cancelar com motivo, no detalhe | não |
| T-pedidos-12 | data proposta já gravada, no detalhe | não |
| T-pedidos-13 | adaptação, no detalhe | não |
| T-pedidos-14 | nota interna, no detalhe | não |
| T-pedidos-15 | reenvio da outbox, no detalhe | não |
| T-pedidos-16 | solicitações, na home e em `/admin/pedidos/solicitacao/{id}` | não |
| T-pedidos-17 | propor outra data, na solicitação | não |
| T-pedidos-18 | pedir complemento, na solicitação | não |
| T-pedidos-19 | encerrar com justificativa, na solicitação | não |
| T-pedidos-20 | aceitar e virar pedido, na solicitação | não |
| T-pedidos-21 | contagem no resumo da home; sem botão próprio | não |
| T-produtos-01 | Catálogo / Produtos, `/admin/produtos` | sim |
| T-produtos-02 | Catálogo / Produtos, `/admin/produtos/novo` | sim |
| T-produtos-03 | Catálogo / Produtos, `/admin/produtos/{id}` | sim |
| T-produtos-04 | ações do editor, no mesmo endereço | sim |
| T-produtos-05 | vitrine na lista de produtos | sim |
| T-produtos-06 | Catálogo / Receitas da semana, `/admin/produtos/receitas` | sim |
| T-produtos-07 | ações na lista de receitas | sim |
| T-produtos-08 | editor, `/admin/produtos/receitas/{id}` e `/nova` | sim |
| T-produtos-09 | Produção / Dias, tetos e fechamentos, `/admin/agenda` | sim |
| T-produtos-10 | Conteúdo / Gigio, `/admin/produtos/gigio` | sim |
| T-produtos-11 | Conteúdo / Harmonizações, `/admin/produtos/gigio/harmonizacoes` | sim |
| T-produtos-12 | Conteúdo / Complementos, `/admin/produtos/complementos` | sim |
| T-agenda-01 | Produção / Dias, tetos e fechamentos, `/admin/agenda` | sim |
| T-agenda-02 | teto do dia, na mesma agenda | sim |
| T-agenda-03 | fechamento, na mesma agenda | sim |
| T-agenda-04 | cancelar ou reabrir, na mesma agenda | sim |
| T-fidelidade-01 | Clientes / Fidelidade, `/admin/fidelidade` | sim |
| T-fidelidade-02 | ajuste no painel do participante | sim |

44 de 44.

## Testes ajustados

`frontend/src/admin/CatalogTabs.test.tsx` continua. A asserção antiga pedia o link “Vitrine e cadastro” com `href` `/admin/produtos`, renderizando `CatalogTabs` em `current="recipes"`. A nova pede o link “Produtos” com o mesmo `href`, no menu (`AdminSidebar`) com `path="/admin/produtos/receitas"`. Receitas da semana (href e `aria-current="page"`), Gigio, Harmonizações e Complementos continuam exigindo os mesmos hrefs.

`frontend/src/admin/stageContract.test.ts` ganhou `/// <reference types="node" />`. Nenhuma asserção mudou. O arquivo saiu do `.dockerignore`. O `tsc` do build usa `tsconfig.build.json` e não inclui testes.

Testes novos em `frontend/src/admin/shell/AdminShell.test.tsx`: itens e hrefs, Parceiros e Repasses sem link, `aria-current` nas rotas preservadas, casca em `/admin/produtos` sem `fetch`, gaveta (Esc, escolha de item e foco de volta), Gigio ausente em `/admin/pedidos` e presente em `/`.

## Capturas

`depois/` tem os mesmos nomes de `readme/evidence/prompt-107/antes/`, em 1280×800 e 390×844, mais `gaveta-aberta-390.png`. Origem `http://127.0.0.1:5175`, banco `lojadepaes_capture`. Pares em `comparacao.md`.

Na captura, de 320 px a 1440 px a página não teve rolagem horizontal. O contraste medido na casca ficou acima de 4,5:1 (marca 17,29; grupo, selo e trilha 5,84; item ativo 6,9; item “em breve” 7,46).

## Publicação

Imagem `lojadepaes:prod-20261029b` (`sha256:b5e3af64357efd90e146469c1d71bf9ff0864156e68573c1539fd5949446bb89`). Retorno `lojadepaes:prod-20261029a`. Backup `lojadepaes-20261029T224409Z.sql.gz`, 118809 bytes, gravado antes da troca. Alembic `d5e9f2a18b33` (head). O backend da imagem é idêntico ao de `prod-20261029a`, ignorando fim de linha. O bundle `index-BgUyJRs3.js` contém “Dias, tetos e fechamentos”. Health e ready públicos: `{"status":"ok","service":"lojadepaes"}`.

O `.tar` local `C:\Temp\loja-prod-20261029b.tar` foi apagado depois do deploy confirmado. Disco C: 51,37 GB livres antes do build e 50,22 GB depois.
