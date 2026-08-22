# Reconciliação CURSOR-012

Compara o prompt de execução, a proposta documental do Cursor (`prompts/CURSOR-012-proposta.md`) e as doze questões do CURSOR-011.

| Tema | Prompt 012 | Proposta Cursor | Questão 011 | Decisão adotada |
|---|---|---|---|---|
| Escopo do ciclo | Fundação persistente: plano, ordem, batelada, dependências, snapshots, liberação, eventos, permissões, RLS | Fatia documental e, se aceito, só desenho de DDL — sem migrar se descoberta pendente | — | **Prompt vence:** há autorização explícita para migrar e implementar o domínio, sem HTTP/frontend |
| Descoberta com usuários | Fechar P1 por defaults na ausência de decisão | Fechar P1 com o proprietário antes do DDL | “antes de cravar o DDL” | Defaults do prompt; P1 restante documentada como limitação (um papel) |
| Formulação na liberação | Aprovada obrigatória | Preservar lab; não usar `trial` | — | Aprovação válida obrigatória; `trial` separado |
| Quem libera | Humano com `production.order.release` | Gestor de produção | Q2 (dupla com técnico?) | Só quem tem `production.order.release`. Técnico **não** recebe liberação neste ciclo. Dupla aprovação = futuro |
| Pesagem | Fora deste ciclo; estados futuros no catálogo | Sem execução | Q3 | Pesagem **não obrigatória** e **sem comandos**. Atalho `released` → `in_progress` fica para ciclo futuro |
| Pré-fermento | Dependências explícitas entre ordens | — | Q4 | Tipo `preferment` em `production_order_dependency` |
| Preparação intermediária | Dependência entre ordens | — | Q5 | Tipo `intermediate`; não vira `trial` nem insumo automático |
| Capacidade de equipamento | Fora (sem cadastro CMMS) | — | Q6 | Sem cadastro; batelada guarda só alvo e memória da divisão |
| Lote / estoque | Não implementa | Fora | Q7 | Fora; estoque não bloqueia ordem |
| QR / ficha renderizada | Não implementa | Sem PDF/quadro salvo GET mínimo (não pedido) | Q8 | Sem QR, PDF ou HTML |
| Offline | Operação digital conectada; ficha = contingência | — | Q9 | Conectado; ficha impressa só como especificação já existente |
| Relógio | Servidor (eventos `occurred_at`) | — | Q10 | Relógio do servidor na gravação do evento |
| Vários estabelecimentos no plano | Um estabelecimento por plano | — | Q11 | Um plano, um estabelecimento |
| Quem vê o quadro | Permissão `production.board.read` (viewer se autorizada) | Sem frontend | Q12 | Concedida a gestor, técnico (leitura), padeiro e viewer. Sem UI neste ciclo |
| Um papel por associação | Preservar; documentar limitação | Não implementar múltiplos papéis | Q1 | **Preservado.** Padeiro que também planeja precisa de outro papel na associação |
| Alteração após liberação | Cancelar + nova ordem (substituta) | — | — | Snapshots imutáveis; ordem substituta com vínculo |
| Custos / conformidade / estoque | Não bloqueiam a ordem além das validações técnicas | Sem custos | — | Só org, produto, formulação aprovada, escala compatível, batelada, dependências acíclicas |
| HTTP / frontend | Não | Não (salvo GET mínimo não solicitado) | — | Sem endpoints de produção |

Defaults aplicados na ausência de decisão explícita do proprietário: (1) aprovação obrigatória; (2) liberação por `production.order.release`; (3) dupla aprovação futura; (4) pesagem fora; (5) pré-fermento = dependência; (6) mudança material = nova ordem; (7) digital conectado; (8) ficha como contingência documental; (9) um papel; (10) estoque/custo/conformidade não bloqueiam.
