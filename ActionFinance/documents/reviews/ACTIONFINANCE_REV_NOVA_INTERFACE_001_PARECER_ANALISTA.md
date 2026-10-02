# Parecer sobre a nova interface do ActionFinance

Data: 02/10/2026. Aceite visual e funcional do recorte: NÃO. Implementação local relatada, não publicada.

## Evidências inspecionadas

Leitura direta de C:\Projetos\ActionFinance\documents\reviews\ACTIONFINANCE_REV_NOVA_INTERFACE_001.md e inspeção visual das capturas 1280-pay-pendencia.png e 360-pay-detalhe.png em documents/reviews/screenshots/nova-interface. Não foram inspecionadas todas as 30 imagens nem repetidos testes nesta revisão. Gates 43/43, lint/build/audit são resultados relatados pelo executor.

## R1 Referências disponíveis e comparação obrigatória

As três imagens existem na área do analista. A afirmação de ausência não corresponde ao estado verificado nesta revisão. Não se conclui por isso qual caminho foi pesquisado pelo executor. Abrir os arquivos abaixo e corrigir o relatório, registrando eventual erro de localização:

- C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\interface-aprovada\01-recebimentos-desktop-mobile.png
- C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\interface-aprovada\02-detalhe-recebimento-desktop-mobile.png
- C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\interface-aprovada\03-acesso-cognito-desktop-mobile.png

Copiar para a pasta documental estável prevista e comparar lado a lado. Texto prevalecer em divergência não dispensa consultar as referências aprovadas. Não substituir silenciosamente a direção gráfica.

## R2 Marca e hierarquia visual

Na captura desktop, a marca é um quadrado branco pequeno sobre navy; não é a marca branca integrada ao cabeçalho azul aprovada. O asset chamado white não basta para comprovar resultado visual correto. Usar a referência oficial azul com lettering branco e ajustar o tratamento do asset sem distorcer/desenhar outra marca. Preservar letras e proporção, evitando margens excessivas. Referência original disponível em C:\Projetos\ActionFinance\frontend\images\action finance logos\logoazul.png.

Há três faixas de navegação/contexto e blocos grandes antes dos dados. Reorganizar conforme a referência: cabeçalho compacto, navegação clara, ações próximas ao título, resumo de sincronização discreto e filtros junto à lista. Manter destinos existentes sem criar busca global fictícia. Na subnavegação desktop, texto branco sobre lilás claro exige medição e correção de contraste; não afirmar conformidade sem evidência.

O detalhe mobile repete rótulos e apresenta grande volume técnico em caixas aninhadas. Aproximar da hierarquia aprovada: cobrado/pago/situação primeiro, pendência concisa, dados disponíveis e rastreio secundário expansível. Não confundir ausência com zero nem esconder informação necessária à conferência.

## R3 Linguagem operacional

Retirar da tela principal explicações sobre paginação da API, contrato e inexistência de dimensões. Essas lacunas pertencem ao relatório técnico. Na captura consta literalmente que a API não pagina e que o contrato não devolve filtros. Mostrar apenas filtros funcionais e ajuda financeira necessária ao operador.

ActionHub Pay é sistema/origem integrada, não automaticamente origem comercial ou estabelecimento. Não rotular essas dimensões como equivalentes. Conservar cobrado/pago, falta de evidência e distinção de saldo, mas com mensagens breves e detalhes acessíveis sob demanda.

## R4 Provas funcionais e mobile

O relatório declara browser com API simulada e ausência de regressão financeira controlada. Isso não cumpre toda a verificação solicitada. Executar jornada local integrada em ambiente descartável: título, baixa parcial, conclusão, estorno, extrato; viewer, troca de empresa, proteção de rascunho e retry/conflito pertinentes às telas alteradas. Não exigir escrita financeira em produção.

A captura mobile fullPage mostra barra fixa cruzando conteúdo. Isso por si só não prova que o conteúdo seja inacessível: conferir no viewport e em rolagem que o último campo, botões, histórico e foco ficam alcançáveis acima da barra, incluindo teclado virtual/zoom quando aplicável. Registrar viewport além de fullPage. Ausência de overflow horizontal não comprova acesso vertical ou foco.

## R5 Cognito ainda incompleto

A adaptação real do formulário permanece pendente. Preparar agora logo e CSS compatíveis com Hosted UI clássico, inventário do client exato, comparação visual possível, configuração anterior para rollback e comando/artefato de aplicação delimitado. Não trocar plano ou versão de login para imitar a prancha sem decisão específica.

Escrita AWS não implica automaticamente nova autorização genérica: examinar a autorização vigente e seu alcance, como exige o prompt. Se não cobrir branding deste client, apresentar apenas essa decisão concreta com pacote pronto e impacto, em vez de deixar preparação por fazer. Não afirmar que o Cognito está personalizado ou validado com uma tela local. Sem nova autorização concedida por este parecer.

## Encaminhamento

Corrigir no mesmo recorte e relatório. Manter a entrega sem aceite até comparação com as referências e provas pertinentes. As omissões de campos sem API e de funcionalidades futuras são corretas; não devem ser compensadas com dados ou controles fictícios. Não alterar produto financeiro, Hub ou Spider para corrigir apresentação. Publicação não é declarada nem autorizada novamente por este parecer.
