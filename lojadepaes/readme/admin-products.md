# Cadastro de produtos — Loja de Pães

Área: http://127.0.0.1:5175/admin/produtos (mesmo login de Pedidos).

## Passo a passo

1. Na vitrine, use Login e Senha no cabeçalho e **Entrar**. O atalho `/admin/login` também leva a esse formulário.
2. Abra **Produtos** e **Novo produto**.
3. Preencha nome e descrição curta. A descrição detalhada é opcional.
4. Envie a foto destacada (JPEG, PNG ou WebP, até 8 MB) e o texto que descreve a imagem.
5. Liste os ingredientes básicos na ordem em que o cliente deve lê-los (composição, sem quantidades de receita).
6. Crie as opções de venda: peso fixo (500 g, 800 g) ou unidade/pacote (1 unidade, pacote com 6). O preço é da opção inteira, no formato `24,90`.
7. **Salvar rascunho** guarda sem aparecer na vitrine. **Publicar produto** exige foto, descrição curta, ingredientes e ao menos uma opção ativa com preço.
8. Na página principal, o pão entra em **Nossos pães**. Se ficar temporariamente sem venda, desmarque a disponibilidade: ele permanece visível, sem compra.
9. Arquivar tira o produto da vitrine sem apagar o cadastro.

O editor reorganiza ingredientes, variações e a barra de publicação em telas estreitas (a partir de 320 px). Subir/descer e o envio de foto por seletor de arquivo precisam continuar usáveis no celular, sem depender de arrastar.

Rascunhos e arquivados nunca aparecem para o cliente. Não há pagamento nesta etapa: a seleção do cliente só guarda pão, opção e quantidade.
