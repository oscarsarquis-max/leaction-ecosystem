# Inventário do miolo — 108B

Desvios do padrão em `readme/backoffice-ui-padrao.md` vistos nas capturas de `readme/evidence/prompt-108b/`. A casca (barra, contêiner, gaveta, painel de avisos) não entra aqui. Nada desta lista foi corrigido. O 109 refaz pedidos, agenda e solicitação. O 110 refaz produtos, receitas e conteúdo.

## Pedidos e agenda — 109

Rotas: `/admin`, `/admin/pedidos`. Capturas `admin-*` e `pedidos-*`.

- Todas as larguras: “Agenda de produção”, “Ciclo dos pedidos” e os títulos do calendário estão em Playfair Display.
- 1280 e 1440: “Hoje” e “Atualizar” têm cerca de 44 px de altura no desktop, raio perto de 2 px e aparência de botão antigo. As setas do calendário são quadrados cinza com raio pequeno.
- 320 e 390: “Agenda de produção” quebra em duas linhas e “Hoje” fica ao lado da segunda linha, fora do eixo do título. “Outubro de 2026” quebra em duas linhas dentro do calendário (`admin-320.png`, `pedidos-320.png`).
- 320, 390, 768, 960, 1280 e 1440: a lista diz “1 pães”.
- 960 e 1280: o calendário e a lista dividem a largura, e o título da agenda não compartilha a coluna dos filtros de uma tela de lista — o bloco ainda é o layout antigo.
- Todas: os números do ciclo (Aberto, Aceito, Pago, Em produção, Entregue) são círculos com rótulo em duas linhas (“Entregue / No histórico”).

## Detalhe do pedido — 109

Rota `/admin/pedidos/{id}`. Capturas `pedido-*`.

- Todas: “← Pedidos” repete a trilha e fica com recuo diferente do bloco de baixo (o link começa antes do cartão).
- 1280 e 1440: o estado “Pago” é um título grande em caixa azul, em Playfair, no lugar de um selo.
- Todas: os avisos saem com chaves técnicas, por exemplo “Aviso order_accepted: skipped — identidade SES ainda não verificada…”, “order_auto_accepted_admin”, “payment_approved” e “payment_sync_alert”.
- Todas: “Data pedida” usa ISO (`2026-11-04`) e o restante da tela usa dd/mm/aaaa.
- 1280: “Cancelar” tem o mesmo peso visual de “Iniciar produção” (os dois são botões cheios, da mesma altura).
- Todas: “Recarregar” é botão antigo, alto no desktop e com raio pequeno.
- 320: o texto dos avisos quebra no meio da frase técnica, sem reticências.

## Solicitação de data — 109

Rota `/admin/pedidos/solicitacao/{id}`. Capturas `solicitacao-*`.

- 320 (`solicitacao-320.png`): o selo “Solicitação de data” e o texto “Aguardando resposta” quebram em linhas soltas, um ao lado do outro.
- 320: “1 pão(ães)”.
- Todas: o código público e os títulos de seção estão em Playfair.
- Todas: “Voltar à fila” é botão antigo, com raio pequeno e altura de toque também no desktop.
- A data desejada aparece como `18/11/2026` no detalhe, enquanto a agenda lista as mesmas solicitações em ISO (`2026-11-18` em `agenda-320.png`).

## Agenda de fornadas — 109

Rota `/admin/agenda`. Capturas `agenda-*`.

- Todas: “Agenda de fornadas”, “Solicitações de data” e “Rotina de A Loja” estão em Playfair.
- 320: as datas das solicitações estão em ISO (`2026-11-18`).
- Todas: “Atender em Pedidos” e os controles da rotina seguem o botão antigo (altura de toque no desktop, raio pequeno).

## Produtos — 110

Rotas `/admin/produtos`, `/admin/produtos/novo`, `/admin/produtos/{id}`. Capturas `produtos-*`, `produto-novo-*`, `produto-*`.

- Todas: “Produtos”, “Editar produto”, “Novo produto” e “Vitrine (10 posições)” estão em Playfair.
- 320 e 390 (`produtos-390.png`): “Filtrar” fica sozinho numa linha, com a largura de um campo.
- 1280 (`produtos-1280.png`): “Subir” e “Descer” ficam colados, sem espaço entre eles.
- Todas: “Novo produto”, “Subir”, “Descer” e “Filtrar” usam o botão antigo, com altura de toque no desktop e raio pequeno.
- 320: o título da vitrine e o texto de ajuda ocupam a largura toda com a tipografia antiga (tamanho fora da escala nos títulos de seção).

## Receitas da semana — 110

Rotas `/admin/produtos/receitas`, `/admin/produtos/receitas/nova`, `/admin/produtos/receitas/{id}`. Capturas `receitas-*`, `receita-nova-*`, `receita-*`.

- Todas: “Receitas da semana”, “Nova receita” e “Editar receita” estão em Playfair.
- 1280: “Salvar rascunho”, “Publicar e destacar na home” e “Publicar sem destacar” são botões antigos, altos no desktop, com raio pequeno. “Arquivar” é um link sublinhado ao lado, sem a mesma altura.
- 320 (`receitas-320.png`): “Destacar” e “Publicar” ocupam a largura do cartão; “Editar” e “Arquivar” ficam em linhas separadas, com o espaçamento do miolo antigo.
- 320: o título da receita quebra no meio da célula (“Receita Exemplo da / Semana”).

## Gigio — 110

Rota `/admin/produtos/gigio`. Capturas `gigio-*`.

- Todas: “Explicações aprovadas” está em Playfair.
- Todas: o identificador técnico (`concept:fermentacao · versão 1`) aparece cru, acima do título.
- Todas: “Salvar” é botão antigo, alto no desktop.

## Harmonizações — 110

Rota `/admin/produtos/gigio/harmonizacoes`. Capturas `harmonizacoes-*`.

- Todas: “Referências de harmonização” está em Playfair.
- 320 (`harmonizacoes-320.png`): os metadados técnicos aparecem crus (`board-mesa-frios · frios · style · pairing_recommendation · pairing · verified · versão 1 · Rascunho`).
- 320: as áreas de texto cortam a frase no meio da linha (“distintas, ambutidas…” e a nota editorial).
- Todas: campos e “Salvar” seguem a altura e o raio antigos.

## Complementos — 110

Rota `/admin/produtos/complementos`. Capturas `complementos-*`.

- Todas: “Para acompanhar seu pão” está em Playfair.
- 320: o texto de curadoria e o estado “O Hub não respondeu agora” usam o bloco antigo, com campos de altura de toque também no desktop.

## Fidelidade — 110

Rota `/admin/fidelidade`. Capturas `fidelidade-*`. Fora do recorte de pedidos; entra no 110 junto do conteúdo.

- Todas: “Fidelidade da casa” e os títulos de seção estão em Playfair.
- 320: “Ver detalhes” é botão antigo, na largura do cartão, com raio pequeno.
- Todas: o CPF mascarado e a contagem “Pedidos válidos no mês” usam a tabela/cartão antigo, com rótulo quebrado em duas linhas no celular.
