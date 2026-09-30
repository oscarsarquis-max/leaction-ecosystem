# Prompt 49 — Editor de receita amplo, simples e com preparo em texto único

O proprietário considera o editor de Receita da semana difícil de usar. A captura mostra controles minúsculos, labels e campos na mesma linha, pouca área para texto/foto e preparo separado em passos com adicionar/subir/descer/remover. **Ele solicitou mais espaço de edição e não quer separar o preparo em passos.** Esta orientação substitui o requisito anterior de editor de passos.

Corrigir no monorepo da Loja de Pães e publicar após validação. Preservar receitas/rascunhos já existentes, imagens, destaque da home, produtos, pedidos, pagamentos e fidelidade. Não assumir que o banco ainda tem zero receitas.

## 1. Corrigir a causa do layout

Inspecionar o formulário renderizado, CSS carregado e seletores. Verificar por que os controles aparecem com aparência padrão e inline. Não resolver reduzindo zoom/fontes nem acrescentando margens aleatórias em cada campo. Aplicar estilos delimitados ao editor, sem alterar globalmente outros formulários.

Container central de até aproximadamente 1200 px, ocupando a largura útil. Textos de formulário 16 px, labels em bloco acima dos campos, inputs com altura confortável e largura 100% do grupo, box-sizing correto. Em desktop, área de conteúdo principal ampla e área de imagem lateral de tamanho útil; em celular, uma coluna. Vãos de 24–32 px e padding internos suficientes, sem metade da página vazia enquanto textos ficam comprimidos.

## 2–8

Ver o pedido integral do proprietário: preparo em textarea único, ingredientes por linha, foto ampla, prévia em aba, publicação após validação sem mutar receitas reais.
