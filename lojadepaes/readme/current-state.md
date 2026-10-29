# Estado atual — Loja de Pães

## Prompt 107 (29/10/2026 — contrato local, sem publicação)

Inventário funcional do backoffice e suíte `backend/tests/contract`, mais `frontend/src/admin/stageContract.test.ts`. Nenhum arquivo de `backend/app/`, `frontend/src` (fora de teste), `database/` ou `infra/` entra neste passo. Não houve migração, imagem nem escrita em produção.

A base informada da loja publicada continua `lojadepaes:prod-20261028c`, Alembic `d5e9f2a18b33`. O restante deste arquivo ainda descreve imagens anteriores e está defasado em relação a esse carimbo. Evidência: `readme/evidence/prompt-107/`.

27/10/2026. Sem senhas, tokens nem URLs internas de banco.

## Prompt 104 / 104A (produção — Gigio)

O atendimento caiu porque o perfil `us.anthropic.claude-sonnet-4-20250514-v1:0` chegou ao fim da vida em 14/10/2026 (`ResourceNotFoundException`). A região continua `us-east-1`. O perfil ativo da mesma família é `us.anthropic.claude-sonnet-4-6`. A permissão de invocar esse perfil foi acrescentada; a do perfil antigo permanece.

A pergunta da vitrine dizia que não havia pães porque `lookup_products` ia com consulta vazia. O contrato recusa consulta vazia e não lista o catálogo. A síntese lia `count: 0` como vitrine vazia e respondia com receitas. Consulta vazia continua inválida. Pergunta explícita sobre a vitrine usa `q=vitrine`, lê a vitrine em exposição e, se a síntese ainda disser que ela está vazia depois de uma consulta concluída com pães, há uma correção. Busca por nome que não acha o pão não esvazia a vitrine.

Imagem `lojadepaes:prod-20261027b` (rollback `prod-20261027a`, que já responde saudação e ainda pode errar a vitrine). Backup `lojadepaes-20261027T131125Z.sql.gz` (105653 bytes). Alembic `c4d8e1f07a22`, sem migração. Prova de API: saudação sem ferramenta; vitrine com `lookup_products` modo showcase, 9 itens, os nove pães publicados e disponíveis na hora; continuidade do café da manhã sem ferramenta nova. Sem captura de navegador.

## Adendo 103A (produção — ciclo ativo)

A lista de Pedidos mostra o ciclo Aberto → Aceito → Pago → Em produção → Entregue. Pendências, pagamentos dos ativos e o histórico abrem no clique. A caixa de testes saiu deste painel. A tabela de receitas do 103 permanece.

Imagem `lojadepaes:prod-20261026b` (rollback `prod-20261026a`). Backup `lojadepaes-20261026T213740Z.sql.gz` (104692 bytes). Alembic `c4d8e1f07a22`. Capturas isoladas: `readme/evidence/prompt-103a/`. Sem sessão administrativa, a tela publicada não foi fotografada.

## Prompt 103 (produção — resumo só em Pedidos e tabela de receitas)

O resumo operacional e a agenda de produção montam só em `/admin` e `/admin/pedidos`. As outras abas administrativas não disparam essas consultas. Notificações neste aparelho abrem pelo botão do cabeçalho, sem pedir permissão ao trocar de aba. A tabela de `/admin/produtos/receitas` fica no mesmo bloco do título, com ações em grade.

Imagem `lojadepaes:prod-20261026a` (rollback `prod-20261024c`). Backup `lojadepaes-20261026T211144Z.sql.gz` (104687 bytes). Alembic `c4d8e1f07a22`, sem migração nova. Evidência isolada: `readme/evidence/prompt-103/`. Sem sessão administrativa, a tela publicada não foi fotografada; o pacote no ar contém o texto novo.

## Adendo 102B (produção — e-mail e notificação no celular)

O alerta automático de WhatsApp deixa de ser requisito. O contato manual da home continua em `https://wa.me/5585999831861`. O e-mail operacional segue o endereço já configurado, sem segundo envio.

A Loja passa a oferecer Web Push administrativo, com par VAPID só no servidor. Não há inscrição ativa e nenhuma notificação foi enviada. Aceitação futura do serviço não comprova que o aviso apareceu no celular. O worker não guarda cache de página, pedido ou pagamento.

Imagem `lojadepaes:prod-20261024c` (rollback `prod-20261024b`; as tabelas e o par VAPID podem permanecer). Backup `lojadepaes-20261025T001419Z.sql.gz` (101900 bytes). Alembic `c4d8e1f07a22`. Evidência: `readme/evidence/prompt-102b/`.

## Adendo 102A (produção — margem da agenda; WhatsApp manual)

O atendimento por WhatsApp existe na home: link `https://wa.me/5585999831861`, sem texto pré-preenchido, no componente `HomeContact`. Continua no pacote publicado. Não há adaptador, webhook, worker nem variável de provedor na Loja, na Panne, no Phanton, na Spider ou no ActionHub. O e-mail operacional segue o endereço já configurado. Nenhuma mensagem automática foi enviada. O envio automático de alertas ainda não foi encontrado.

A agenda de produção deixa de encostar na borda. A seção inteira usa a mesma largura máxima de 1100 px e a centralização do conteúdo administrativo, com 20 px nas laterais no desktop e 16 px no celular. Captura isolada em `readme/evidence/prompt-102a/`. Sem sessão administrativa, não há captura da tela publicada.

Imagem `lojadepaes:prod-20261024b` (rollback `prod-20261024a`). Backup `lojadepaes-20261024T233943Z.sql.gz` (101906 bytes). Alembic `f9c2a6e81b04`, sem migração nova. Evidência: `readme/evidence/prompt-102a/`.

## Prompt 102 (produção — testes fora da operação, agenda e alertas)

Seis registros de teste saíram da fila comercial, da agenda e dos indicadores, por marcador reversível, sem apagar pedido nem conta. São os cinco cancelados “rastro 145” (`LP42E1CA0A1A`, `LP72EC1CB055`, `LP7968212021`, `LP242E207138`, `LP18AE314D6C`) e o cancelado “oscar sarquis” (`LPB0DA668D3F`). Nenhum ocupava reserva. O total vigente era 0 e continuou 0. A fila comercial ficou em 12; a lente administrativa de testes ficou em 6.

Ficaram para revisão, visíveis: `LP87D4BCF4E1` e `SD51A91EFF` (“oscar s g braga”) e `LP23FF6F00E2`, concluído em 23/09/2026, ainda com reserva. A reserva não foi liberada.

A tela de Pedidos abre com a agenda do mês, pela data da fornada combinada, no fuso America/Sao_Paulo. Em outubro há três pedidos históricos, um por dia: `LP42BF063F0C` (06/10), `LP7C58FF0190` (09/10) e `LPF891F9E5D1` (23/10). Não houve captura autenticada no navegador.

O e-mail operacional continua o endereço já configurado. WhatsApp está implementado e desligado: sem provedor oficial e sem número administrativo confirmado. Nenhuma mensagem foi enviada. O número da vitrine não entrou como destinatário.

Imagem `lojadepaes:prod-20261024a` (rollback `prod-20261021e`; tabelas novas podem ficar). Backup `lojadepaes-20261024T231727Z.sql.gz` (101137 bytes). Alembic `f9c2a6e81b04`. Evidência: `readme/evidence/prompt-102/`.

## Adendo 101C (produção — pedido em andamento visível)

`LPF891F9E5D1`, de `SD3CC4C139`, voltou a Em produção por correção assistida. Às 12:38 de 21/10 a conta administrativa iniciou a produção e, três segundos depois, marcou pronto. O pagamento de R$ 70,00 já estava registrado desde 09:23 e foi preservado, junto com a reserva e o endereço pendente. Não houve entrega nem aviso novo. Pronto sem confirmação de entrega permanece no total vigente como exceção, fora da sequência principal. `unique_records` usa o mesmo total do quadro.

Imagem `lojadepaes:prod-20261021e` (rollback `prod-20261021d`). Backup `lojadepaes-20261021T183136Z.sql.gz` (99561 bytes). Alembic `e8a1b7c42d19`, sem revisão nova. Leitura posterior: vigentes 5 = Pago 3 + Em produção 2. A exceção Pronto está em 0. O pedido está na lente Em produção, pago na faixa financeira, com endereço incompleto ainda marcado. Evidência: `readme/evidence/prompt-101c/`.

## Adendo 101B (produção — estados, cores e produção sem pagamento)

O fluxo visível do gestor é Aberto, Aceito, Pago, Em produção e Entregue. Entregue exige a ação Confirmar entrega e o carimbo `delivery_confirmed_at`. Pronto (`ready`) e Finalizado (`completed` sem o carimbo) ficam no histórico com o significado original. Pagamento e etapa operacional continuam separados: quitação posterior não tira o pedido de Em produção. Iniciar produção com valor pendente pede confirmação explícita, permissão administrativa e registro do estado financeiro observado. Cinza de Aberto e azul de Pago completam cores que o proprietário não definiu; amarelo, verde, branco e vermelho pastel são as cores definidas.

Imagem `lojadepaes:prod-20261021d` (rollback `prod-20261021c`). A imagem `prod-20261021c` publicou as transições e a coluna; `21d` inclui o Pronto histórico no marcador de endereço incompleto. Backup `lojadepaes-20261021T172710Z.sql.gz` (99560 bytes). Alembic `e8a1b7c42d19`, sem preencher entregas. Leitura de 21/10/2026 14:27, horário de Brasília, sem filtro de data de criação e sem gravação: vigentes 4 (Pago 3 e Em produção 1), Entregue 0, Finalizado 4, Pronto 1, Cancelado 8, Rejeitado 1, endereço incompleto 1. `LPF891F9E5D1` (de `SD3CC4C139`) continua `ready`, pago, com endereço pendente e sem confirmação de entrega. Pedidos, solicitações, avisos e cobranças permaneceram 17, 4, 52 e 18. Evidência: `readme/evidence/prompt-101b/`.

## Prompt 101 (produção — resumo gerencial dos pedidos)

O resumo administrativo deixa a lista sobreposta e a frase “Nenhuma pendência prioritária agora”. No lugar: fluxo vigente (avaliação, confirmados, em produção, prontos), histórico à parte (finalizados, cancelados, solicitações encerradas) e faixas separadas de pagamento e pendências. O clique só filtra a fila. Não há Enviados nem Entregues: o domínio não registra expedição nem prova de entrega. Leitura de 21/10/2026 12:18, horário de Brasília, sem filtro de data de criação: 5 vigentes, 17 pedidos na faixa de pagamento, 4 aguardando pagamento e 13 pagos. `LPF891F9E5D1` (de `SD3CC4C139`) está confirmado e pago, com endereço de entrega ainda incompleto. A leitura não gravou. Imagem `lojadepaes:prod-20261021b` (rollback `prod-20261021a`). Backup `lojadepaes-20261021T151728Z.sql.gz`. Alembic `d7e0f5a24b38`, sem migração. Evidência: `readme/evidence/prompt-101/`.

## Prompt 100 (produção — aceite com quantidade já informada)

Solicitação com quantidade persistida e pão só na mensagem deixa de cair na trava “faltam os pães e as quantidades”. O administrador confirma o produto do catálogo na própria área de aceite, vê o preço vigente e o total, e o clique em Aceitar cria um pedido, reserva e o aviso de pagamento. Endereço e telefone ficam como pendência, sem bloquear. A solicitação `SD3CC4C139` permanece pendente, sem pedido e sem e-mail de aceite: a prévia só de leitura sugere o pão de nome único, 1 × 500 g, R$ 70,00, e o aceite continua com o proprietário. Imagem `lojadepaes:prod-20261021a` (rollback `prod-20261011a`). Backup `lojadepaes-20261021T115706Z.sql.gz`. Alembic `d7e0f5a24b38`, sem migração. Agenda, login, home, receitas e Pay intocados. Evidência: `readme/evidence/prompt-100/`.

## Prompt 99 (produção — enquadramento das receitas)

O cartão de destaque passou a ter quadro 16:9 com `cover` local e `image_focus` publicado. A sopa deixa de aparecer pequena no centro com faixas. Leitura permanece foto integral (`contain`). Acervo continua sem foto. Imagem `lojadepaes:prod-20261011a` (rollback `prod-20261009e`). Backup `lojadepaes-20261011T194521Z.sql.gz`. Vitrine 98, pães, marketplace, logos, Gigio, Agenda, pedidos e Pay intocados. Evidência: `readme/evidence/prompt-99/`.

## Prompt 98 (produção — vitrine na abertura da home)

A foto da massa e o selo lateral da abertura foram substituídos pela vitrine autorizada. “O despertar do levain”, o título e o parágrafo à esquerda permanecem. Coluna visual ~metade da área útil no desktop; uma coluna no tablet/celular. Imagem `lojadepaes:prod-20261009e` (rollback `prod-20261009d`). Login 97, contratação 95B e Agenda 96B intocados. Evidência: `readme/evidence/prompt-98/`.

## Prompt 97 (produção — login Entrar e Receber código)

Popover Identifique-se: e-mail **ou** CPF, Código de acesso, Entrar e Receber código. Admin pelo formulário **Acesso administrativo** (Usuário / Senha). Código continua temporário (15 min, uso único); sessão 30 dias. Imagem `lojadepaes:prod-20261009d` (rollback `prod-20261009c`). Contratação 95B e Agenda 96B intocadas. Evidência: `readme/evidence/prompt-97/`.

## Adendo 95B (produção — autorização e identidade da Loja)

Contratação da Biblioteca deixa de dizer que a recorrência já foi autorizada antes do cartão. Consentimento e ação ficam na página; a autorização acontece no brick do Mercado Pago no dashboard — não por e-mail. Títulos “Sua assinatura da Biblioteca” / “Suas consultas de IA”. Sem ActionHub no texto do cliente. Login: Entrar e Receber código distintos. Hub FE `CDuEURE9hD2FC62PJaE4U`. Loja `lojadepaes:prod-20261009c` (rollback `prod-20261009b`). Pay, Agenda e planos comerciais intocados. Percurso oficial do Mercado Pago **não** exercitado. Evidência: `readme/evidence/prompt-95b/`.

## Adendo 96B (produção — formulário de outra data)

Quantidade pretendida deixa de nascer com 2. Formulário novo vazio; aceita 1; vazio não vira 1 nem 2. Orientação permanente sem “inclusive para hoje”; aviso de fechamento continua o da Agenda. Imagem `lojadepaes:prod-20261009b` (rollback `prod-20261009a`). Fechamento da Agenda não foi reconfigurado. Evidência: `readme/evidence/prompt-96b/`.

## Adendo 95A (produção — logo Hub)

`/brands/lojadepaes.png` passou de 404 para 200 (`image/png`, 125797 bytes). Arquivo oficial da Loja. BUILD_ID `RcbKeSmRZ78ehM6EjRi82`. Evidência: `readme/evidence/prompt-95a/`.

## Prompt 96 (produção — Agenda)

Fechamento configurável de período. Viagem 10–18/10; bloqueio de novas datas 10–20/10; recebimento aberto para fornadas a partir de 21/10. Sem pausa geral.

| Item | Evidência |
|---|---|
| Imagem | `lojadepaes:prod-20261009b` (96B; rollback de app: `prod-20261009a`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T111435Z.sql.gz` |
| Alembic | `d7e0f5a24b38` |
| Fechamento | até 20/10 · `pause_intake=false` · autor `admin:admin@lojadepaes.com.br` |
| Compromissos no intervalo | nenhum pedido nem solicitação aberta |
| Evidência | `readme/evidence/prompt-96/` |

## Prompt 95 (produção — Hub FE)

Causa do “This page couldn’t load” em `/loja`: `resolveClientBrand('lojadepaes')` nulo → `brand.colors`. Publicado só o frontend do Hub. Loja sem republicação.

| Item | Evidência |
|---|---|
| Página restaurada | https://actionhub.com.br/loja e a URL com `return_origin` / `return_to` |
| BUILD_ID Hub FE | `ODrRI9FZL2AwRMNrQtqEx` |
| Backup Hub | `leaction_hub_20261009T102421Z` + `p95-20261009T102421Z` |
| Loja | `lojadepaes:prod-20261008g` (inalterada) |
| Jornada | home → Biblioteca → Ver planos → R$ 19/mês e R$ 10 avulso → `/loja/contratar` (sem submit) |
| MP oficial | **não exercitado** — produção e gateway local estão em `APP_USR` / `sandbox_mode=false` |
| Evidência | `readme/evidence/prompt-95/` |

Não encerrado como plenamente pronto: falta o percurso oficial de teste do Mercado Pago.

## Prompt 94 (produção)

Exceção temporária Loja–Hub para planos. Spider permanece sandbox. Pay de pão não foi alterado.

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008g` (rollback de app: `prod-20261008f`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261009T000337Z.sql.gz` |
| Alembic | `c6d9e4f13a27` — tabela `hub_plans_events` |
| Regras | `94` |
| Ingresso planos | `POST /api/v1/webhooks/actionhub/plans` |
| Ingresso Pay | `POST /api/v1/webhooks/actionhub` (inalterado) |
| Evidência | `readme/evidence/prompt-94/` |
| 94A | Encerrada. Sem novo deploy. Cadeia isolada + UI pública conferidas. MP sandbox não exercitado. |

## Adendo 91H (código local; não ativado)

Fluxo Spider 1.5 permanece no repositório para migração futura. Produção 94 usa `hub_plans.py`.

Fluxo de planos da Biblioteca passa a ser Loja → capacidades Spider 1.5 → Hub. Pay de pão fora. Visitante vê Identifique-se. 10% de assinante aplica junto com resgate de pão, em linhas separadas. Evidência: `readme/evidence/prompt-91h/`.

## Produção (Adendo 91G)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008f` (rollback de app: `prod-20261008e`) |
| Bundle | `/assets/index-B-aP-XuE.js` + `index-pwEhWLTn.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T182428Z.sql.gz` |
| Alembic | `b5c8d3e02f16` — sem migração nova |
| Regras | `91` (87–90 preservados) |
| Planos oficiais | https://actionhub.com.br/loja · contratar https://actionhub.com.br/loja/contratar |
| Principal | R$ 19/mês · 20 consultas de IA · 10% nos produtos da Loja · `subscription` |
| Pacote adicional | R$ 10 avulso · 10 consultas de IA · `hub_brick` · não é assinatura |
| Identidade | cabeçalho / carrinho do Hub; código no e-mail cadastrado |
| Domínios | Assinatura ≠ Consultas de IA ≠ Fidelidade / créditos de pão |

Evidência: `readme/evidence/prompt-91g/`.

## Produção (Adendo 91B)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008e` (rollback de app: `prod-20261008d`) |
| Bundle | `/assets/index-Cp6IkaW8.js` + `index-DsQJyzwt.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T141759Z.sql.gz` |
| Alembic | `b5c8d3e02f16` — operação de crédito para reconciliação |
| Regras | `91` (87–90 preservados) |
| Preços exibidos | Principal R$ 19,00/mês · 20 créditos; complementar R$ 10,00/mês · 10 créditos |
| Planos no Hub | **sem ID** — catálogo `lojadepaes` ainda vazio; checkout fechado |
| Consumo | cliente Loja pronto; API Hub `POST /v1/credits/*` no repositório, não no gateway de produção |
| Monetização | apresentação ≠ assinatura autorizada ≠ consumo funcionando |

Evidência: `readme/evidence/prompt-91b/`. Ficha: `scripts/p91-hub-plan-sandbox.md`.

## Produção (Prompt 91 + Adendo 91A)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008d` (rollback de app: `prod-20261008c`) |
| Bundle | `/assets/index-DpP7aSCr.js` + `index-BaODGZlW.css` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T135317Z.sql.gz` |
| Alembic | `a4b7c2d91e05` — uso do Gigio + cache de autorização |
| Regras | `91` (90 preservado) |
| Artigos / calculadora | abertos, sem modelo |
| Plano Hub | SKU `LOJADEPAES_BIBLIOTECA_MENSAL` ainda não publicado no editor; checkout fechado |
| Pedidos / Pix / fidelidade / Fazedor | independentes da assinatura |

Evidência: `readme/evidence/prompt-91/`. Contrato do plano: `scripts/p91-hub-plan-sandbox.md`.

## Produção (Prompt 90)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008c` (rollback de app: `prod-20261008b`) |
| Bundle | `/assets/index-DGjt2ALe.js` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T130009Z.sql.gz` |
| Alembic | `f3c9a1b28e04` — sem migração |
| Regras | `90` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

CTA comercial e **Montar esse pão** só na intenção atual. Hambúrguer → Fusca não cria botão novo. Evidência: `readme/evidence/prompt-90/`.

## Produção (Prompt 89)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008b` (rollback de app: `prod-20261008a`) |
| Bundle | `/assets/index-DGjt2ALe.js` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T121410Z.sql.gz` |
| Alembic | `f3c9a1b28e04` — sem migração |
| Regras | `88` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

No Criador, a dica do Gigio aparece no passo **A forma** sem abrir o chat flutuante. Sem formato, o bloco pede a escolha. Menu público: **Crie seu pão**. Evidência: `readme/evidence/prompt-89/`.

## Produção (Prompt 88)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261008a` (rollback de app: `prod-20261007o`) |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261008T085505Z.sql.gz` |
| Alembic | `f3c9a1b28e04` — sem migração |
| Regras | `88` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Instrução interna (`<invoke>`) não vai mais ao cliente: recuperação ou falha explícita. Evidência: `readme/evidence/prompt-88/`.

## Produção (Prompt 87)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007o` (rollback de app: `prod-20261007m`; não usar `h` nem o `n` incompleto) |
| Bundle | `/assets/index-jO8kSabC.js` |
| Backup | `/opt/lojadepaes/backups/lojadepaes-20261007T231219Z.sql.gz` |
| Alembic | `f3c9a1b28e04` — sem migração |
| Regras | `87` |
| Gigio comum / vitrine / complementos | ligados |
| Hub | inalterado (86): vinhos, queijos, frios, azeites, cervejas, batatas |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Gigio propõe composição validada do Criador (**Montar esse pão**). O Criador mostra dica da composição atual antes da revisão. Data excepcional (focaccia / hoje) permanece a jornada 68. Evidência: `readme/evidence/prompt-87/`.

## Produção (Prompt 86)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007m` (rollback de app: `prod-20261007k`; não usar `h`) |
| Bundle | `/assets/index-B1EglQRL.js` |
| Alembic | `f3c9a1b28e04` — sem migração |
| Piloto especializado | **ligado** — 83 + 84 + 84A intactos |
| Flag | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Regras | `86` |
| Gigio comum / vitrine / complementos | ligados |
| Hub | perfil A Loja com vinhos, queijos, frios, azeites, **cervejas** e **batatas**; cartão só com `availability_verified` |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Hambúrguer com batatas e bebidas abre cervejas e batatas verificadas no Mercado Livre, não Canastra. Título **Para o hambúrguer**. Sem álcool tira cerveja e vinho. 85A: sem «Mesa de fim de tarde» repetido; sem cartão sem verificação. Evidência: `readme/evidence/prompt-86/`.

## Produção (Prompt 85)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007k` (rollback de app: `prod-20261007j`; não usar `h`) |
| Bundle | `/assets/index-Demy9U2N.js` |
| Alembic | `f3c9a1b28e04` — sem migração neste incremento |
| Piloto especializado | **ligado** — 83 + 84 + 84A intactos |
| Flag | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Regras | `85` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

A mesma resposta do Gigio volta a trazer **Ver acompanhamentos sugeridos** quando há oferta compatível. Sardinhas: fonte Wine Folly + receita publicada + azeites do Hub (sem alargar o filtro de vinho). Frios e peixe grelhado (Vinho Verde) confirmam a jornada com oferta real. Evidência: `readme/evidence/prompt-85/`.

## Produção (Adendo 84A)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007i` (rollback de app: `prod-20261007g`; não usar `h`) |
| Bundle | `/assets/index-DUyLrOkC.js` |
| Alembic | `f3c9a1b28e04` |
| Piloto especializado | **ligado** — 83 + 84 + duas avaliações Descorchados verificadas |
| Flag | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Regras | `84a` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Avaliações disponíveis ao Gigio: Sacramentos Vinifer Sabina Entre Serras Sauvignon Blanc 2025 (95/100) e Casa Almeida Barreto Paralelas Cabernet Franc 2024 (94/100), Informe Brasil 2026. ADEGA 2026 está cadastrada como localizador; fichas individuais pendentes. Sem oferta do Hub com essas identidades. Evidência: `readme/evidence/prompt-84a/`.

## Produção (Prompt 84)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007g` (rollback de app: `prod-20261007f`; não usar `h`) |
| Bundle | `/assets/index-B1tJLCHz.js` |
| Alembic | `e2b8f4a07d91` |
| Piloto especializado | **ligado** — 83 + mesa de frios, peixe grelhado, sardinhas, camarão leve, lagosta |
| Flag | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Evidência: `readme/evidence/prompt-84/`. Outros crustáceos como classe e camarão com molho picante continuam lacuna.

## Produção (Prompt 83)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | `lojadepaes:prod-20261007f` (rollback de app: `prod-20261007d`; não usar `h`) |
| Bundle | `/assets/index-B1tJLCHz.js` |
| Alembic | `d1a6e3b15c82` |
| Piloto especializado | **ligado** — só `wine-churrasco-porco` e `wine-queijo-tabua` |
| Flag | `LOJADEPAES_GIGIO_PAIRING_REFS_ENABLED=true` (runtime) |
| Gigio comum / vitrine / complementos | ligados |
| Pedidos / Pix / fidelidade | ligados, sem mudança |

Evidência: `readme/evidence/prompt-83/`.

## Produção (Prompt 80)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ e https://lojadepaes.com.br/acompanhar |
| Imagem | `lojadepaes:prod-20261007d` (rollback de app: `prod-20261007c`; não usar `h`) |
| Bundle | `/assets/index-BuTqGpTP.js` |
| Hub | plugin marketplace pontual; rollback `rollback-prompt80-20261007T150020Z` |
| Vitrine | 29 itens no catálogo geral; CTA da mesa com 8 itens e título «Sugestões para sua mesa» |
| Gigio complementos | ligado — CTA sem exigir pedido explícito de vinho |
| Pedidos / Pix / fidelidade | ligados |

Evidência: `readme/evidence/prompt-80/`.

## Produção (Prompt 78)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/acompanhar |
| Imagem | era `lojadepaes:prod-20261007c` (rollback: `prod-20261007b`) |
| Hub | plugin marketplace republicado; rollback `rollback-prompt78-20261007T140649Z` |
| Vitrine | perfil culinário sem gravata/livro/chaveiro/Mikasa; 28 itens válidos na carga quente |
| Gigio complementos | ligado |
| Pedidos / Pix / fidelidade | ligados |

Evidência: `readme/evidence/prompt-78/`.

## Produção (Prompt 77)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ e https://lojadepaes.com.br/acompanhar |
| Imagem | `lojadepaes:prod-20261007b` (rollback de app: `prod-20261006k`; não usar `h`) |
| Bundle | `/assets/index-zwbhWtVP.js` |
| API | `GET /api/v1/health` e `/ready` = ok |
| Postgres | Lightsail `lojadepaes-app`; Alembic **`b8e4c1d93f50`** |
| Vitrine pública | ligada; origem Hub `lojadepaes`; 32 itens; URL contextual `cats`/`tipo`/`ids` |
| Gigio complementos | **ligado** — CTA «Ver acompanhamentos sugeridos» abre `/acompanhar` filtrado |
| Gigio comum | ligado |
| Pedidos / Pix / fidelidade | ligados |

Evidência: `readme/evidence/prompt-77/`.

## Produção (Prompt 76)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ e https://lojadepaes.com.br/acompanhar |
| Imagem | `lojadepaes:prod-20261006k` (rollback de app: `prod-20261006j`; não usar `h`) |
| Bundle | `/assets/index-UyX9NXP6.js` |
| API | `GET /api/v1/health` e `/ready` = ok |
| Postgres | Lightsail `lojadepaes-app`; Alembic **`b8e4c1d93f50`** |
| Vitrine pública | ligada; origem Hub `lojadepaes`; 32 itens em grade 3/2/1, 12 por página |
| Gigio complementos | desligado |
| Gigio comum | ligado |
| Pedidos / Pix / fidelidade | ligados |

## Produção (Prompt 75)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ e https://lojadepaes.com.br/acompanhar |
| Imagem | era `lojadepaes:prod-20261006j` (rollback de app: `prod-20261006g`; não usar `h`) |
| Bundle | era `/assets/index-DilXU1VT.js` |
| API | `GET /api/v1/health` e `/ready` = ok |
| Postgres | Lightsail `lojadepaes-app`; Alembic **`b8e4c1d93f50`** |
| Vitrine pública | ligada; origem Hub `lojadepaes`; 32 itens com link/foto oficiais |
| Gigio complementos | desligado |
| Gigio comum | ligado |
| Pedidos / Pix / fidelidade | ligados |

## Produção (Prompt 54, histórico)

| Item | Evidência |
|---|---|
| HTTPS | https://lojadepaes.com.br/ |
| Imagem | era `lojadepaes:prod-20261006g` (rollback de app: `prod-20261006f`) |
| Bundle | era `/assets/index-Cx6V3SbN.js` |
| API | `GET /api/v1/health` e `/ready` = ok |
| Postgres | Lightsail `lojadepaes-app`; Alembic então **`a7d3b8e02c41`** |
| Pedidos / Pix | ligados; fila única de encomendas e solicitações de data (Prompt 67) |
| Fidelidade | `carimbos-da-casa` ativa |
| Receita em destaque | **Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)** |
| Aviso à padaria | `LOJADEPAES_MAIL_OPS_TO` ativo para avisos operacionais reais; remetente Loja de Pães `<loja@lojadepaes.com.br>` |

## Prévia local (Prompt 74)

http://127.0.0.1:5175/ e http://127.0.0.1:5175/acompanhar. Flags só no `.env` local. Pães e receita em destaque vieram do catálogo público. Complemento é fixture identificada (Hub `:4012` fora). Sem deploy. Evidência: `readme/evidence/prompt-74/`.

## Complementos (Prompt 75)

Publicado. Perfil A Loja no Hub (vinhos/queijos/frios/azeites) isolado do legado TI. Marketplace em `https://actionhub.com.br/marketplace-api`. Vitrine pública ligada; Gigio de complementos desligado. Overlay da Loja vazia — sem associação no pão até o proprietário anexar narrativa. Fixture local não foi a produção. Evidência: `readme/evidence/prompt-75/`.

## Complementos (Prompt 73)

Estrutura de **Para acompanhar seu pão** realinhada ao perfil do Hub: legado continua TI; app id `lojadepaes` pede vinhos/queijos/frios/azeites. Overlay local só narrativa/pães — não é catálogo de preço ou link. Admin: `/admin/produtos/complementos`. Evidência: `readme/evidence/prompt-73/`.

Na vitrine a lista longa de ingredientes abre sem repetir o preview. A revisão `/pedido/novo` usa container de 1080 px e quantidade editável com cotação do servidor. Pedido já enviado continua só leitura. O CTA do Criador só leva ao fechamento. Nome e e-mail são exigidos antes de persistir. Novos avisos administrativos saem pela outbox transacional; skipped antigos não são promovidos. Configuração pronta não prova entrega na caixa.

## Atendimento (Prompt 72)

Fila vigente continua o padrão. **Todos** inclui finalizados e cancelados. Busca por nome cobre o histórico completo (Osvaldo → `LP2BEEEFEB18`). Endereço de `LP42BF063F0C` não estava no pedido — só rua incompleta na solicitação; sem recuperação inventada. Focaccia passa a contar para carimbo e não pode ser prêmio; o pedido real não tinha participação, então não foi carimbado nem o ajuste manual foi mexido. Publicado `prod-20261006g`; rollback `f`. Sem e-mail, cobrança ou bonificação de teste. Evidência: `readme/evidence/prompt-72/`.

## Atendimento (Prompt 71)

O link do e-mail de `LP42BF063F0C` (`/pedido/LP42BF063F0C`) passou a mostrar **Pagar com Pix** e **Pagar com cartão** sem endereço. Causa: a tela pedia `/operations` e o fallback só liberava `submitted`; pedido em produção ficava com título Pagamento e sem ação. A API já tinha `payment_available`. Publicado `prod-20261006f`; rollback `prod-20261006e`. Backup `20261006T143731Z`. Alembic inalterado. Sem novo e-mail. Sem clique em Pix/cartão reais. Prova isolada no href do HTML gerado; prova de produção por leitura do link autorizado (390). Evidência: `readme/evidence/prompt-71/`.

## Atendimento (Prompt 70)

O e-mail de aceite passou a ser a comunicação única de pagamento e endereço, com logo oficial. O link antigo de solicitação abre o pedido protegido. O formulário de endereço do checkout salva e reabre. Publicado `prod-20261006e`; rollback `prod-20261006d`. Backup `20261006T140336Z`. Alembic inalterado. Comunicação corretiva de `LP42BF063F0C` já tinha sido enviada com chave `prompt70` — sem reenvio. O endereço digitado agora persiste no link antigo e no pedido; o pedido real continua sem entrega até a cliente preencher de novo. Evidência: `readme/evidence/prompt-70/`. Prompt 69 não tinha mudanças no repositório.

## Atendimento (Prompt 68)

Aceite de solicitação com itens e preço resolvidos formaliza pedido, reserva e pagamento **sem exigir endereço**. Falta de endereço vira “Dados de entrega pendentes” no pedido, no e-mail e na página protegida; o cliente pode pagar antes de completar a entrega. Publicado `prod-20261006c`; rollback `prod-20261006b`. Backup `20261006T085825Z`. Alembic inalterado (`a7d3b8e02c41`). Caso real `SD15BD4592` recuperado como `LP42BF063F0C`. Evidência: `readme/evidence/prompt-68/`.

## Atendimento (Prompt 67)

Pedidos é a fila operacional única. Solicitações de data aparecem com selo, “Sem cobrança” e “Avaliar e responder”. Aceite formaliza pedido, reserva e manda o link de pagamento; proposta de outra data não reserva; encerrar exige justificativa por e-mail. Pedido padrão da vitrine segue para pagamento automaticamente. Publicado `prod-20261006b`; rollback `prod-20261006a`. Backup `20261006T060336Z`. Evidência: `readme/evidence/prompt-67/`.

## Atendimento (Prompt 66)

O e-mail de 05–06/10 era solicitação de data, não pedido. Nada se perdeu no banco. Pedidos agora mostra aviso para a Agenda; `submitted` antigo volta à lista. Publicado `prod-20261006a`; rollback `prod-20261001j`. Backup `20261006T043842Z`. Evidência: `readme/evidence/prompt-66/`.

## Navegação (Prompt 65)

Fora da home o menu aponta para `/#paes`, `/#criacao`, `/#mural` e `/#biblioteca`. Todas as páginas internas têm o retorno textual «Página principal». Na home o item aparece como atual. Publicado `prod-20261001j`; rollback `prod-20261001i`. Evidência: `readme/evidence/prompt-65/`. Inclui a correção do Prompt 64 no mesmo bundle.

## Modalidade (Prompt 63)

Novos pedidos são somente entrega, com endereço obrigatório. Sem escolha retirada/entrega e sem frete. O passo 4 do Criador usa o calendário da home. Publicado `prod-20261001i`; rollback `prod-20261001h`. Evidência: `readme/evidence/prompt-63/`. Pedidos históricos de retirada permanecem como estavam.

## Contatos na home (Prompt 61)

Faixa «Fale com A Loja» antes do rodapé: WhatsApp `wa.me/5585999831861` e Instagram `@loja.de.paes`. Publicado `prod-20261001h`; rollback `prod-20261001g`. Evidência: `readme/evidence/prompt-61/`. O link não prova entrega de mensagem.

## Detalhe do pão (Prompt 62)

`/paes/{slug}` (Pão de Canela e os demais) tinha `main.product-page` com `padding: 32px 0`, o mesmo tipo de override do Prompt 60, em outra rota. Publicado `prod-20261001g`; rollback `prod-20261001f`. Evidência: `readme/evidence/prompt-62/`. Sem iPhone físico.

## Margens e Gigio (Prompt 60)

Leitura `/receitas/{slug}`, revisão `/pedido/novo` e confirmação `/pedido/{ref}` com respiro lateral ≥16 px no celular. Causa na leitura: `padding: 32px 0` no `main` da receita. Gigio deixa de cobrir a busca e as ações (recuo no celular + avatar fechado). Cartão em destaque mantido em 320 px — a medida anterior era 448 px; sem redesenho. Publicado `prod-20261001f`; rollback `prod-20261001d`. Evidência: `readme/evidence/prompt-60/`. Confirmação após envio comprovada só em fixture isolada.

## Receita em destaque (Prompt 59)

Correção da faixa bege à direita e da foto alta demais. Causa: `.week-recipe-media` com `flex-start` e `max-height: 28rem`. Publicado `prod-20261001d`; rollback de app `prod-20261001c`. Evidência: `readme/evidence/prompt-59/`.

## Home (Prompt 58)

O formulário «Precisa de outra data?» fica aberto na primeira carga, no bloco verde, abaixo do calendário. Sem o link «Sugerir uma data». Publicado `prod-20261001c`; rollback de app `prod-20261001b`. Alembic inalterado. Evidência: `readme/evidence/prompt-58/`.

## Gigio (Prompt 57)

Correção pontual da resposta culinária. Causa: laço de ferramentas esgotava e o backend mentia «consulta longa demais», anexando todos os links das tools. Publicado `prod-20261001b`; rollback de app `prod-20261001a`. Alembic inalterado (`c8e2f1a90b64`). Evidência: `readme/evidence/prompt-57/`.

| Etapa | Estado |
|---|---|
| Pergunta exata em produção | Resposta culinária útil, sem erro falso de comprimento |
| Links | Só o pão citado (Fermentação Natural de Trigo); não anexa Café/Pan con Tomate sem citação |
| Flag | `LOJADEPAES_GIGIO_ENABLED=true`, `live=true` |

## Gigio (Prompt 56 / 56B)

Contrato identificado no **Chamelleon** (`C:\Projetos\chamelleon`): Bedrock Runtime `invoke_model`, Anthropic Messages `bedrock-2023-05-31`, inference profile `us.anthropic.claude-sonnet-4-20250514-v1:0`, região **us-east-1** (SES permanece us-east-2).

| Etapa | Estado |
|---|---|
| 56A publicado | Sim — textos de atendimento usam **A Loja** no bundle `index-ZkR9G8Kr.js` |
| Gigio publicado | Sim — imagem vigente `prod-20261001b` (56B: `prod-20261001a`) |
| Gigio ativo | Sim — `LOJADEPAES_GIGIO_ENABLED=true`, `live=true`, respostas reais do Bedrock |

Identidade de produção `lojadepaes-prod` recebeu só `bedrock:InvokeModel` no perfil/modelo Chamelleon (sem wildcard). Backup PG `20261001T112326Z`. Evidência: `readme/evidence/prompt-56/`.

## Editor

**Produtos → Receitas da semana** — https://lojadepaes.com.br/admin/produtos/receitas

## Desenvolvimento local

| Item | Endereço |
|---|---|
| Frontend Vite | http://127.0.0.1:5175/ |
| API | http://127.0.0.1:5075/ |
| Postgres | 127.0.0.1:5438, banco `lojadepaes` |
