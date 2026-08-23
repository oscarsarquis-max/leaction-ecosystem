# Arquitetura da informação canônica

A marca Panne leva ao início. Não existe o domínio “Cadastros”. Criação (“Novo ingrediente”, “Nova receita”) permanece dentro do módulo.

Primeiro nível horizontal:

1. Marca (início)
2. Produção
3. Receitas
4. Componentes
5. Conformidade
6. Gestão (só com permissão)
7. Organização e usuário à direita, fora da lista de domínios

## Submenus aprovados

- **Produção:** Quadro, Planejamento, Ordens, Rastreabilidade
- **Receitas:** Minhas receitas, Biblioteca e referências, Fichas técnicas, Testes e aprovações
- **Componentes:** Ingredientes, Preparações e bases, Fornecedores e itens, Unidades e conversões, Nutrientes, Alergênicos, Fontes técnicas
- **Conformidade:** Biblioteca normativa, Avaliações, Pendências e evidências
- **Gestão:** Organização, Estabelecimentos, Pessoas e acessos, Papéis e permissões

“Propostas assistidas” permanece só no histórico do UX-001 (Atelier/Oficina/Mesa). A direção aprovada remove esse item.

O cromado (domínio + trilho) vem da Oficina. O breadcrumb e o ritmo da página vêm do Atelier. Item ativo usa `aria-current`; submenu usa `aria-expanded`. Escape fecha. Sem interação exclusiva por hover.
