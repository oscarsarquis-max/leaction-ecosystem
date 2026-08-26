# Matriz de rotas do assistente

Fonte: `collectRouterPaths()` + `buildAssistantMatrix()`. Papel: perfil demo vigente. Avatar: shell autenticado (login público no `/entrar`).

| Rota | Página | Guia | Entidade | Próxima ação |
|---|---|---|---|---|
| /entrar | Entrar | específico | sessão | Entrar com o provedor da organização |
| /inicio | Início | específico | atalhos | Ir ao quadro ou ao cadastro |
| /producao | Quadro de produção | específico | ordem | Definir contexto ou executar |
| /planejamento | Planejamento | específico | plano | Abrir um plano |
| /ordens | Ordens | específico | ordem | Abrir a ordem |
| /rastreabilidade | Rastreabilidade | específico | evento | Abrir uma ordem |
| /receitas | Receitas | específico | receita | Abrir uma receita |
| /componentes/ingredientes | Ingredientes | específico | ingrediente | Abrir ou criar |
| /componentes/estoque | Estoque | específico | saldo | Abrir posição |
| /componentes/lotes | Lotes | específico | lote | Revisar bloqueados |
| /componentes/fornecedores | Fornecedores | específico | fornecedor | Abrir item |
| /conformidade | Conformidade | específico | dossiê | Abrir um dossiê |
| /gestao/custos | Custos e preços | específico | cálculo | Abrir previstos |
| /gestao/compras/necessidades | Necessidades | específico | sugestão | Abrir requisição |
| /gestao/inventarios | Inventários | específico | sessão | Revisar |
| /gestao/relatorios | Relatórios | específico | relatório | Abrir a visão |

Rotas dinâmicas (detalhe, execução, ficha, snapshot) resolvem pelo padrão `:id` e entram na mesma matriz automática dos testes.
