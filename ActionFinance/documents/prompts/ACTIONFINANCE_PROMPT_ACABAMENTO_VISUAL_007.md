# ActionFinance alinhamento e acabamento das telas operacionais

Identificador: ACTIONFINANCE_PROMPT_ACABAMENTO_VISUAL_007. Data: 02/10/2026. Destinatário: Cursor. Documento novo e independente. Preservar os prompts anteriores.

## Evidência e objetivo

O proprietário aponta desalinhamento e falta de cuidado na tela pública Contas a receber. Na captura enviada, a busca é estreita e corta o placeholder; categoria ocupa uma caixa de altura e borda diferentes dos demais filtros; checkbox Só vencidos aparece grande e descolado do rótulo; botão Limpar e campos não formam uma composição coerente. O seletor de empresa ocupa quase toda a faixa do cabeçalho. Há grandes intervalos sem função entre busca e filtros.

Tratar como defeito de acabamento da entrega, não como pedido de redesenho completo. A hierarquia de duas barras foi aprovada e permanece. Corrigir os componentes e composições compartilhados, sem nova rodada de mudanças de menu e sem declarar sucesso apenas por ausência de overflow horizontal.

Captura de referência do defeito: C:\Users\OSCARS~1\AppData\Local\Temp\codex-clipboard-edcc60b2-6d8b-4a8b-b06a-6ab521b40311.png. Se o arquivo temporário já tiver expirado, reproduzir a tela atual, não inventar a evidência. Referências aprovadas: C:\Projetos\ActionFinance\documents\ux\interface-aprovada.

## Correção da composição de filtros

Organizar duas linhas compactas e coerentes no desktop:

1. Busca com largura útil flexível e botão Filtros alinhado à caixa de entrada, não ao topo do rótulo. Placeholder curto, como “Referência ou descrição”, sem usar placeholder como substituto do label.
2. Quando expandido, grid de Situação, Situação financeira, De, Até, Categoria, Só vencidos e Limpar. Labels acima dos campos; controles alinhados pela mesma linha de base, com alturas consistentes. Quebrar em novas linhas por breakpoint antes de comprimir rótulos e valores.

Não exigir tudo numa única linha em larguras insuficientes. Adotar espaçamento consistente, por exemplo 16 px entre campos e 16–24 px entre grupos, como token compartilhado e ajustável após inspeção. Evitar margens individuais para “empurrar” cada campo até parecer alinhado em um único viewport.

Categoria pesquisável não deve aparecer como cartão com duas caixas empilhadas no meio de uma linha de controles simples. Usar um combobox acessível de um campo com busca e seleção ou outra solução equivalente de mesma altura fechada, reaproveitando componente adequado existente quando possível. Preservar busca, seleção, teclado, estado vazio e sem resultados; não sacrificar função por estética. A proibição de menus suspensos de navegação não proíbe a lista de opções de um campo de formulário.

Checkbox Só vencidos: caixa visual pequena e proporcional, alinhada horizontalmente ao texto, com área clicável confortável no conjunto. Investigar se regra CSS genérica de input está impondo tamanho de campo de texto. Não reduzir a área de interação junto com o desenho da caixa. O rótulo deve ativar o controle e o foco permanecer visível.

Limpar é ação secundária alinhada ao grupo de filtros; distinguir visualmente de ação primária financeira. Filtros deve expandir/recolher de modo real e acessível, com estado comunicado e sem apagar escolhas silenciosamente. Mostrar filtros ativos de forma compreensível quando recolhidos.

## Cabeçalho, resumo e área útil

Preservar marca branca horizontal sobre #1603AD e duas barras paralelas. Dar largura proporcional ao seletor de empresa, evitando esticá-lo por quase todo o desktop. Nome, usuário e Sair devem ficar legíveis e integralmente acessíveis, sem rótulo cortado. Verificar se corte observado é da captura ou do layout antes de atribuir a causa. Nome longo precisa de estratégia responsiva, sem esconder contexto.

Título e ação principal alinhados na mesma composição, com quebra adequada no mobile. Reduzir espaços verticais sem função entre resumo, busca e filtros. Manter hierarquia e respiração; não comprimir tudo.

Resumo financeiro com tipografia e unidades consistentes: por exemplo, número e “itens” na mesma linha quando forem contagem auxiliar. Não transformar soma de títulos em caixa ou saldo bancário. Não alterar fórmulas, filtros financeiros ou dados para ajustar a aparência.

## Revisão transversal obrigatória

Inspecionar A receber e A pagar, filtros de transações importadas, cadastros, contas financeiras, formulários e detalhe. Identificar usos dos mesmos componentes antes de mudar CSS global. Evitar seletores genéricos que apliquem largura/altura de textbox a checkbox, radio, botões ou ícones.

Padronizar labels, alturas de controles de texto, espaçamento, bordas, raios, alinhamento de botões, foco e mensagens de validação. Não inserir avisos sobre API/contrato na interface operacional. Não reintroduzir sidebar, Mais ou menus de navegação suspensos.

## Prova visual e funcional

Reproduzir a tela com os filtros expandidos. Inspecionar manualmente capturas de viewport em 360, 768, 1280 e uma largura desktop ampla próxima à captura do proprietário (aproximadamente 1848 px). Registrar dimensões efetivas; não redimensionar a imagem para esconder desalinhamento.

Conferir alinhamento de campos/botões, placeholder e valores legíveis, nomes longos, checkbox proporcional, labels e foco. Mobile deve empilhar os campos em ordem de leitura, sem overflow da página. Avaliar zoom 200%, navegação por teclado, abrir/fechar filtros e opções da categoria, limpar filtros e persistência ao voltar da lista/detalhe.

Capturar antes/depois das mesmas telas e estado, lado a lado. Medidas geométricas e testes de componentes apoiam a prova, mas não substituem inspeção visual. Declarar quais imagens foram efetivamente abertas e revisadas pelo executor. Não entregar “30 capturas” sem verificar seu conteúdo.

Executar lint, testes pertinentes e build. Preservar semântica dos filtros, resultados/contagens e permissões. Verificação com dados de teste em ambiente controlado é distinta da consulta pública autenticada; não escrever fatos financeiros em produção para gerar telas preenchidas.

## Publicação e entrega

Corrigir dentro do recorte de interface autorizado, preservar rollback e publicar pelo canal vigente após os gates. Verificar versão final e as mesmas telas no host público. Não reiniciar Spider nem alterar Cognito, Hub/Pay, Panne, contratos ou banco.

Criar ACTIONFINANCE_REV_ACABAMENTO_VISUAL_007.md com causa dos problemas de layout, componentes afetados, comparação antes/depois, verificações desktop/mobile, versão e limitações. Copiar este prompt para documents/prompts como arquivo novo e indexar, sem alterar instruções anteriores.

Aceite visual permanece NÃO até a comparação efetiva. Menu publicado, teste verde e ausência de overflow não equivalem a interface bem acabada. O executor não concede autoaceite nem transfere ao proprietário uma nova suíte de tentativas.
