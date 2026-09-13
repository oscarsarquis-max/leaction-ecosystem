# SEGSENSE_PRM_012_COR_001 — Correção única da âncora comercial

## Controle

- Projeto: SegSense; versão 1.0; data: 12/09/2026.
- Corretivo **único** do `SEGSENSE_PRM_012`, ainda não aprovado.
- Execução pelo Cursor somente em `C:\Projetos\segsense`, no monorepo `leaction-ecosystem`.
- Não iniciar PRM_013, provider mock, Spider/Icatu real, migração, login, commit, push ou deploy. Não alterar outros produtos ou `.cursor/`.

## Prompt para o Cursor

Leia integralmente `SEGSENSE_PRM_012`, `SEGSENSE_REV_012`, `SEGSENSE_POS_001`, `SEGSENSE_UX_005`, `SEGSENSE_ASM_001`, as páginas `/` e `/demonstracao/icatu`, seus estilos e testes. Preserve a pesquisa `SEGSENSE_SRC_002` e o contrato conceitual `SEGSENSE_MCK_001`; esta correção não amplia o escopo técnico.

### Evidência do desvio

Na inspeção independente da rota `http://127.0.0.1:5178/` em browser, o texto e a rota estão corretos, mas a composição desktop apresenta um painel à direita quase todo vazio, com apenas três linhas concentradas no meio. O título ocupa quatro linhas e os CTAs ficam abaixo da primeira dobra numa janela aproximadamente 1265×900. Isso contraria o aceite do PRM_012: hierarquia comercial convincente, sem grande área vazia injustificada, e próximo passo claramente perceptível. A faixa “Em validação — Prova visual da jornada pública e identidade administrativa” revela uma pendência de QA interna ao visitante B2B. O texto “A Spider não é dona do SegSense” é verdade arquitetural, mas formulação defensiva para a vitrine; explique papéis e independência de modo positivo e simples. Não esconda limitações reais ao ajustar a linguagem.

O usuário mostrou outra evidência decisiva: a tela que ele efetivamente usa é `http://127.0.0.1:5178/admin/demonstracoes`, com navegação administrativa, título “Apresentações demonstrativas” e somente o aviso “A autenticação administrativa ainda não está configurada”. Nela **não há acesso visível à vitrine pública**. Portanto, o problema de “não vejo o que mudou” não se resolve apenas melhorando `/`; há também uma falha de descoberta a partir da superfície administrativa. Não confunda esta tela protegida com `/` nem prometa liberar o backoffice sem IdP.

### Correção delimitada

1. Recompose o hero da home com hierarquia e equilíbrio visual. Título, proposta de valor, ganho atual e pelo menos um CTA visível na primeira tela desktop 1440×900; em 320×568, o propósito e o próximo passo devem ser discerníveis sem rolagem longa. O painel lateral deve ter conteúdo visualmente útil ou ser absorvido numa composição mais compacta. Não adicione ilustração de apólice, produto/cliente inventado, métrica fictícia ou ornamento que finja integração.
2. Substitua a pendência de QA na vitrine por estado comercial honesto e inteligível: capacidade hoje versus composição futura dependente de contratos. A lacuna da inspeção `/c/{token}` e do admin continua documentada em `SEGSENSE_REV_012`, **não** é argumento de venda. Reduza linguagem interna (`Satellite Contract`, “Spider não é dona”) no texto principal; numa seção técnica secundária, preserve fronteiras corretas e a indisponibilidade de integração. 
3. Mantenha a formulação estratégica: SegSense distribui oportunidades contextualizadas e compõe jornadas explicáveis com seguradoras/intermediários autorizados; produto genuinamente novo pode surgir por co-desenvolvimento com seguradora, não por geração automática. Não transformar hipótese de conversão em resultado mensurado. Icatu segue cenário separado e não oficial; não reinserir agricultura. Preserve disclaimer e privacidade.
4. Revise a home e a demo por teclado, foco, ordem de leitura, contraste e zoom 200%, além de 1440×900, 768×1024, 390×844 e 320×568, **se houver browser real**. Registre evidência visual por viewport sem tokens, credenciais ou dados pessoais. Caso não haja browser, declare a lacuna claramente e forneça testes automatizados e instruções reproduzíveis; não marque a prova como executada. O aceite visual final continuará comigo.
5. Na tela administrativa de demonstrações **quando exibir o bloqueio de autenticação**, inclua uma ação claramente nomeada “Ver apresentação pública do SegSense” para `/` e, se fizer sentido, uma segunda ação “Ver cenário demonstrativo Icatu — não oficial” para `/demonstracao/icatu`. São apenas links de navegação pública, sem endpoint admin, login fictício ou afrouxamento de autorização. O usuário deve conseguir sair do beco sem saída da captura e enxergar o resultado desta etapa em um clique. Preserve o aviso de que editar/aprovar/publicar histórias continua indisponível sem identidade. Teste os links a partir do estado 401.
6. Mantenha `/` público, link visível para `/demonstracao/icatu`, `/admin` protegido e `/c/{token}` intacto. Ajuste apenas componentes, estilos, testes e documentação necessários. Teste root navigation, conteúdo e ausência de afirmações enganosas. Rode lint, testes e build do frontend, `mvnw.cmd verify` do backend; reporte resultados verdadeiros. Sem migration nova.

Atualize `SEGSENSE_REV_012` com o desvio, a mudança e a evidência pós-correção; indexe e arquive cópia integral deste corretivo como `documents/SEGSENSE_PRM_012_COR_001.md`. Na devolutiva, informe URLs, resumo visual antes/depois, limites do browser, testes, arquivos tocados e Git. **Pare para auditoria e aprovação; não inicie PRM_013.** Se persistirem ressalvas, elas serão transportadas para o próximo prompt, pois não haverá segundo corretivo do PRM_012.
