# Fechamento da candidata de clientes e fornecedores

Documento independente para o Cursor. ACTIONFINANCE_PROMPT_FECHAMENTO_CADASTROS_014. Data 05/10/2026.

A revisão 013 resolveu parte importante das pendências. Não reinicie o projeto. Concentre este ciclo na importação mobile, no acabamento dos campos e nas provas finais da candidata. Publicação e migração do RDS continuam sem autorização neste documento.

## Parecer sobre a revisão 013

Foram lidos o relatório 013, V19, trechos do script de captura e do teste de upgrade, a renderização da importação e os resultados Surefire disponíveis. Foram abertas as imagens 1280-cadastrar-vazio-rest, 1280-cadastro-completo-rest, 360-cadastro-completo-scroll e 360-importacao-erro-full. O analista não executou novamente a suíte nem acessou o origin.

Considero atendidos, no alcance da evidência local inspecionada: separar duplicidade de cadastro concluído; exigir resposta com ID e consultar o registro gravado; verificar edição no mesmo ID; inserir dados em V13 antes do upgrade; comparar vínculos e valor depois; corrigir o espelho por identidade completa e diagnosticar colisão entre pessoas. Os resultados Surefire consultados registram 15 + 1 + 3 testes de diretório sem falhas. Preserve essas provas e as correções anteriores.

A grade desktop melhorou. A captura de rolagem mobile mostra o nome abaixo do cabeçalho, sem a faixa sobre o campo. Isso encerra a suspeita baseada apenas na costura da captura longa, dentro do recorte observado; não é aceite integral de usabilidade.

## Importação utilizável no celular

Há uma falha funcional, não apenas uma limitação da evidência: em 360 a prévia não apresenta as linhas. A captura mostra somente totais e confirmação desabilitada. A tabela usa desktop-table e não há apresentação equivalente visível nesse recorte. O operador não consegue conferir qual registro falhou e por quê, nem selecionar individualmente os válidos.

Implemente cartões ou outra apresentação responsiva no fluxo da página, preservando todos os dados necessários de cada linha: número, nome, documento conforme permissão, classificação, motivo, seleção permitida e resultado. Não esconda informações ou controles essenciais em telas menores. Mantenha a confirmação individual e as proteções de duplicidade, prévia obsoleta e idempotência.

Prove no navegador em 360 e 768, com cliques nessas larguras, um arquivo sintético misto com linha válida, inválida e possível duplicidade. Confira os motivos, selecione apenas a válida, confirme, consulte o registro persistido e demonstre que as demais não foram gravadas. Prove também a repetição da confirmação do mesmo lote sem duplicação. Use base isolada; não execute importação produtiva. Preserve a prova desktop existente, repetindo-a apenas se a mudança a afetar.

## Acabamento dos campos de documento

Em 1280-cadastrar-vazio-rest, País do documento quebra em duas linhas e desloca sua caixa abaixo das outras. Tipo do documento corta Não informado. Ajuste a grade para alinhar as caixas pela mesma base e dar espaço ao texto selecionado. Teste também CNPJ e Outro, zoom de 200% e larguras 360/768/1280, sem rolagem horizontal da página.

Não refaça a navegação nem introduza Mais, sidebar ou menu suspenso de navegação. Preserve as duas barras e o azul oficial. Reduza avisos repetidos de que cadastro não autoriza pagamento; essa distinção deve permanecer no comportamento e aparecer na interface quando ajudar uma decisão, sem dominar a ficha cadastral.

## Uma candidata coerente e limites das provas

As capturas 013 usaram banco local V18; V19 foi testada separadamente em Testcontainer. Execute a jornada final em ambiente descartável com a mesma revisão de código e schema V19. Registre commit, versão do schema e identificação do build. Não use a aplicação pública para completar esse ensaio.

Voltar à lista e reabrir o ID comprova nova consulta, mas não recarga do navegador. Faça uma recarga real do detalhe em ambiente de teste autorizado, tratando a reautenticação caso a sessão de demonstração seja perdida, e retorne ao mesmo ID. Não altere a segurança da aplicação nem persista tokens de forma improvisada só para o teste. Não peça senha, MFA ou cookies pelo chat.

O INSERT com colunas antigas comprova compatibilidade dessa instrução SQL. Não comprova rollback da imagem anterior. Corrija essa conclusão no novo relatório e no pacote operacional. Para comprovar rollback, execute a versão anterior efetiva em ambiente isolado com schema expandido, verifique inicialização/Flyway, leitura e gravação compatível e integridade dos campos novos após edição pelo fluxo antigo. Não recolha a imagem pública para fazer a prova. Se o artefato anterior não estiver disponível, registre esse impedimento precisamente; não substitua a prova por um INSERT.

O ensaio em cópia restaurada do origin continua como requisito pré-publicação. Este pedido não autoriza restauração produtiva ou infraestrutura com custo. Prepare o procedimento exato, destino isolado, proteção do dump e invariantes a comparar. Se faltar autorização ou acesso para obter a cópia, apresente esse ponto separadamente depois de concluir todo o restante autorizado; não o confunda com falha da interface.

## Entrega e critério de encerramento

Entregue ACTIONFINANCE_REV_FECHAMENTO_CADASTROS_014 e novas evidências identificadas, preservando 012/013. Apresente uma tabela curta com resultado e evidência para: importação mobile por linha, alinhamento, código/schema da candidata, recarga real, rollback da versão anterior e cópia restaurada. Diferencie não executado de reprovado.

Não amplie o cadastro, não acrescente integrações nem reabra requisitos já comprovados. Sem alteração de Pay, Spider, Panne, Cognito ou operações financeiras. A candidata será avaliada por essas pendências concretas; não declarar aceite do proprietário nem publicar automaticamente.
