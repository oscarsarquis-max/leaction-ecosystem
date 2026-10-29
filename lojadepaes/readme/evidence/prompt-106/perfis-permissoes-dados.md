# Perfis, permissões e dados

29/10/2026. Matriz proposta. Nada disto está implementado, salvo o acesso único descrito abaixo.

## O que existe

Um usuário configurado entra se o nome coincidir com `settings.admin_username` e a senha conferir (`admin_auth.py:168`). A sessão expira, pode ser revogada e o CSRF é verificado. Tentativas são limitadas por usuário e origem. A autoria gravada é `admin:{username}` ou `system:auto-accept`.

Não há organização, papel, segundo fator nem escolha de contexto. `app_id` da Loja no Hub identifica o aplicativo da cobrança, não um parceiro.

Referência de isolamento: [OWASP Multi Tenant](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html). Papéis de tratamento de dados pessoais ficam para validação jurídica. Parceiro não vira automaticamente operador nem controlador. [Guia de agentes da ANPD](https://www.gov.br/anpd/pt-br/assuntos/noticias/nova-versao-do-guia-dos-agentes-de-tratamento).

## Como o contexto deve funcionar

Uma pessoa pode acumular papéis autorizados em organizações autorizadas. Cada sessão de trabalho declara a organização ativa. O servidor confere o vínculo nessa organização em toda leitura e escrita: API, arquivo, busca, relatório, notificação e tarefa automática. Filtro na interface não isola.

Troca de contexto gera nova autorização, não só um rótulo na tela. Pedido, arquivo e alerta carregam a organização dona. Dispositivo inscrito em push só recebe eventos das organizações daquele vínculo.

## Matriz de ações

Leitura (L) ou escrita (E). Escopo: Loja, parceiro próprio, ou plataforma. Motivo: obrigatório quando a ação altera dinheiro, publicação ou exceção. Segunda aprovação (2) quando indicada.

| Ação | Proprietário | Atendimento | Financeiro | Qualidade | Produção Loja | Gestor parceiro | Operador parceiro | Logística | Auditoria |
|---|---|---|---|---|---|---|---|---|---|
| Ver fila da própria organização | L | L | L | L | L | L próprio | L tarefas próprias | L volumes | L |
| Ver cliente, endereço e telefone | L | L | — | — | só o necessário à entrega da Loja | — | — | só endereço e janela do volume | L com trilha |
| Aceitar tarefa de produção | E | — | — | — | E Loja | E próprio | — | — | — |
| Embalar e informar componente | E | — | — | — | E Loja | E | E próprio | — | — |
| Publicar kit | E 2 | — | — | E propõe | — | — | — | — | — |
| Aprovar parceiro | E 2 | — | — | E evidencia | — | — | — | — | — |
| Alterar conta de recebimento | E 2 | — | E propõe | — | — | E propõe a própria | — | — | — |
| Ver preço de fornecimento | L | — | L | — | — | L próprio | — | — | L |
| Ver participação e extrato | L | — | L | — | — | L próprio | — | — | L |
| Ajustar repasse | E 2 motivo | — | E motivo | — | — | — | — | — | — |
| Solicitar estorno ao cliente | E 2 motivo | E propõe | E | — | — | — | — | — | — |
| Exceção de produção sem quitação | E motivo | — | — | — | E motivo, regra atual | — | — | — | — |
| Conferir kit e trocar custódia | E | — | — | L | L | — | — | E | — |
| Exportar dados de clientes | E 2 motivo | — | — | — | — | — | — | — | L registro da exportação |
| Receita e imagens | L | — | — | E versão | L da ficha necessária | L da ficha da própria tarefa | L da ficha da tarefa | — | L |
| Cancelar kit | E motivo | E propõe | L efeito | L se qualidade | L | L efeito na própria tarefa | — | L | — |

Célula “—” significa sem acesso àquele dado, não apenas botão escondido.

## Testes negativos ainda não escritos

Troca de ID na URL; filtro de parceiro manipulado; exportação de outro parceiro; arquivo de outro parceiro; busca global que vaza; mensagem de fila com organização adulterada; push entregue a dispositivo sem vínculo; parceiro que gera carga e não degrada a fila da Loja. Nenhum desses testes existe hoje porque não há segunda organização. Não foram executados.

## Privacidade no kit

O operador do parceiro recebe a quantidade, a ficha do componente, a janela e o identificador do volume. Não recebe a lista de outros itens do cliente, o histórico de compras nem o extrato da Loja. A marca no rótulo não concede o painel.

Dados de cliente para a entrega conjunta ficam com quem o modelo logístico ratificar como transportador e consolidador. Se a consolidação for na Loja, o parceiro não precisa do endereço do cliente.
