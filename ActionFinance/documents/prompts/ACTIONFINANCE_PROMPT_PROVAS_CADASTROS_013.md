# Revisão das provas e acabamento de clientes e fornecedores

Documento independente para o Cursor. Identificador ACTIONFINANCE_PROMPT_PROVAS_CADASTROS_013. Data 05/10/2026.

A candidata 012 avançou na validação de documentos e integridade, mas ainda não recebe aceite visual nem autorização de publicação. Resolva os pontos abaixo no ambiente isolado e entregue evidência verificável. Não reaproveite este pedido como adendo a um prompt anterior.

## Base da análise

Foram lidos o relatório 012, o pacote 011 atualizado, DocumentNumbers, V16/V18, PartyDirectorySchemaUpgradeIT, o script capture-cadastros-012.mjs e trechos do serviço e repositório de cadastros. Foram abertas as capturas 1280-cadastrar-sem-busca, 360-cadastro-completo e 1280-importacao-erro. Esta revisão não executou testes, não consultou o RDS e não afirma ter inspecionado as 24 imagens.

As FKs compostas e connection_key NOT NULL estão presentes. O validador contém os cálculos de DV. O relatório corrigiu a informação do origin para V13 e distingue Testcontainer de cópia restaurada. Preserve essas correções. Os 17 testes permanecem evidência relatada pelo executor.

## Prova de cadastro e detalhe

A captura 360-cadastro-completo mostra “Este documento já identifica outro cadastro nesta empresa” e permanece no formulário Cadastrar. Não comprova cadastro concluído. O script salva cadastro-completo e detalhe consecutivamente, sem navegar nem verificar sucesso. Usa esperas fixas após o envio e não exige ID persistido.

Corrija o ensaio: prepare dados sintéticos em base descartável com estado conhecido; espere a resposta de gravação; confirme identidade e dados persistidos; abra o detalhe desse ID; recarregue e confira os mesmos dados. Faça a tentativa duplicada como caso separado. O teste deve falhar quando o estado esperado não existir, em vez de apenas produzir PNGs. Não apague registros produtivos para repetir a prova.

Mostre cadastro mínimo, cadastro com unidade/endereço/contato/fornecimento, edição e recarga, duplicidade e acesso somente leitura. Confira também o cadastro rápido no título. Registre quais etapas foram clicadas em cada largura e quais foram apenas fotografadas após redimensionar.

## Acabamento e linguagem

A captura mobile apresenta faixa azul sobre os campos no meio da imagem e espaço vazio superior. Pode ser composição da captura de página longa com elemento fixo; não atribua causa sem reproduzir. Confira a tela visível em repouso e durante rolagem, além da captura completa, em 360/768/1280. Cabeçalho não pode ocultar campo focado ou ação.

No desktop, o formulário continua uma coluna longa com todos os campos ocupando a largura inteira. Organize identificação e endereço em grade com proporções adequadas; uma coluna no celular. Alinhe título, formulário e ações, preservando as duas barras aprovadas e o azul oficial. Não introduza Mais, sidebar ou menu suspenso de navegação.

Remova da interface frases internas como “Não invente número”, “Nenhum campo é inventado” e “Isto não é conector Panne”. Use instruções úteis: documento opcional, endereço que pode ser completado depois e formatos aceitos. Na importação, traduza INVALID e ajuste singular/plural (“1 linha”, “1 inválido”). A ação de confirmar deve ficar indisponível quando não houver linha elegível selecionada, com motivo compreensível.

## Preenchimento inicial da autoridade de documentos

V16 usa ON CONFLICT DO NOTHING ao preencher counterparty_document_claim a partir de pessoas e unidades. Isso pode descartar silenciosamente uma colisão preexistente, mantendo dados conflitantes nas tabelas de origem. Quando pessoa e unidade principal compartilham o documento, a inserção da pessoa ocorre primeiro; a inserção da unidade é ignorada, sem registrar o espelho nessa etapa.

Prepare uma prova de upgrade com dados inseridos ANTES da correção de integridade: documento de pessoa sem unidade; documento próprio de unidade; espelho válido da principal; conflito entre pessoas/unidades; unidade inativa. Exija cobertura de cada documento, proprietário correto e espelho correto. Conflito deve interromper o ensaio com diagnóstico ou seguir tratamento explicitamente revisado, nunca escolher silenciosamente um dono. Não modifique migration aplicada sem verificar histórico; escolha correção incremental apropriada.

Na validação do serviço e no repositório, compare a identidade completa (país, tipo e número), não apenas o número normalizado, ao decidir espelhamento. Cubra a igualdade do número com país/tipo diferentes e a existência de mais de uma unidade candidata a principal. Comprove que nenhuma atualização de espelho fica silenciosamente sem efeito ou substitui uma unidade pela última da lista.

## Limite da prova de upgrade e reversão

PartyDirectorySchemaUpgradeIT aplica o schema e depois verifica títulos da base de demonstração. Isso não basta para demonstrar preservação de dados existentes antes da migração. Acrescente ensaio que pare em V13, insira dados de referência e vínculos, aplique V14–V18 e compare IDs, valores e vínculos. Teste o código anterior contra o schema expandido antes de declarar rollback de imagem compatível.

O ensaio em cópia restaurada do origin continua pendente conforme o próprio relatório. Preparar um script e testar sua recusa ao host público não equivale a executá-lo sobre uma cópia. Mantenha essa distinção na entrega. Não restaure sobre produção, não migre o RDS e não crie infraestrutura com custo neste pedido.

## Entrega

Entregue relatório novo ACTIONFINANCE_REV_PROVAS_CADASTROS_013 com achado, correção, teste e limite por item. Preserve as evidências 012; identifique as capturas que não provavam o estado anunciado. Gere novas capturas com URL/ID e estado esperado registrados sem credenciais ou dados pessoais produtivos. Entregue prévia visual revisada para avaliação.

Não publique, importe em produção ou conceda aceite. Não altere Pay, Spider, Cognito, Panne, pagamentos ou os demais ciclos financeiros. O objetivo deste pedido é encerrar as lacunas observadas, sem refazer partes já comprovadas nem ampliar o escopo funcional.
