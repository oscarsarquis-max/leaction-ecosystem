# SEGSENSE_PRM_017_COR_001 — Aceite visual e linguagem humana da jornada

## Controle

- Projeto: SegSense. Versão 1.0. Data: 14/09/2026.
- Este é o **único corretivo** de `SEGSENSE_PRM_017`. Não iniciar PRM_018 e não autoaprovar.
- Auditoria no navegador da versão nova: `http://127.0.0.1:15178/demonstracao/mvp-integrado`. O fluxo URL familiar → intenção entender → resultado `READY` funcionou e exibiu itens somente após a resposta. A captura enviada pelo patrocinador mostrou desalinhamento grave dos controles da intenção em largura desktop; a inspeção em viewport estreita confirmou controles exagerados e texto técnico em área pública.
- Cursor: alterar somente `segsense/`, `spider/` e `segsense-provider-mock/` se indispensável. Preserve a stack antiga e dirty worktree alheio. Sem commit, push, deploy, reset de volume ou parada de processo não pertencente ao ledger.

## Prompt para o Cursor

Corrija a experiência da rota **nova e ativa**. Não trate testes DOM como aceite de layout. O usuário identificou visualmente que radios e checkboxes ficam separados de suas frases, com grandes vazios e alinhamento quebrado; além disso, “Enviar ao SegSense” e “voltar ao SegSense” são incoerentes porque o visitante já está no SegSense. A auditoria também viu identificadores como `UNDERSTAND_PROTECTION_OPTIONS`, `BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO` e `scenarioKey` ocupando o texto explicativo principal. A jornada precisa ser compreensível para corretora/seguradora sem esconder a evidência técnica, que deve ficar em detalhes.

### 1. Corrigir layout na causa, não com remendo de viewport

Inspecione a cascata CSS global (`form input { width: 100%; ... }`, `form label { display: block; ... }`) contra `integrated-mvp.css`. Radios/checkboxes devem ter tamanho natural/adequado, `flex: none` ou equivalente, alinhamento vertical com o texto e alvos acessíveis ≥44 px, sem espaçamento artificial entre controle e rótulo. Rótulo inteiro deve ser clicável. Use classes locais ou regras específicas da página que não alterem formulários de admin, `/c/{token}` ou outros produtos. Mantenha boa leitura e ordenação em desktop/tablet/mobile e zoom 200%. Corrija qualquer overflow horizontal, texto cortado ou quebra indevida de cards; não reduza a fonte para mascarar desalinhamento.

### 2. Linguagem de navegação e ação

O cabeçalho deve dizer exatamente para onde o link leva, por exemplo **“Voltar à apresentação”** (`/`), não “voltar ao SegSense”. O logo pode levar à apresentação, com `aria-label` equivalente. O botão principal deve expressar a ação do visitante nesta página, por exemplo **“Ver possibilidades ilustrativas”** ou “Solicitar análise deste contexto”, sem afirmar que a Spider já recebeu/decidiu. Não use “Enviar ao SegSense”, pois o usuário já está nele. Preserve o estado de espera correto: request iniciado no browser/BFF, sem alegar fases internas. Revise todos os labels, títulos e CTAs da rota para consistência entre SegSense, Spider e Test Double; não renomeie tecnicamente os produtos na trilha de auditoria.

### 3. Explicação de negócio primeiro, prova técnica depois

O campo `explanation` público deve continuar vindo da **Spider**, sem substituição inventada pelo frontend. Ajuste a geração na Spider para uma frase humana baseada **nos elementos e na intenção realmente considerados**: fonte governada e/ou tema declarado; regra explícita; resultado; possibilidade de encaminhamento ao Test Double. Não exponha na frase principal enum, `scenarioKey`, nome de capability, ID ou versão de contrato. Esses valores permanecem em `details` técnicos, com `decisionId`, `providerRequestId` e `providerReference` somente se houver evento confirmado. Diferencie “opções ilustrativas” de etapas operacionais; se o mock só puder devolver passos de conversa, nomeie-os como **próximos passos**, não como serviços/produtos de proteção. Não invente nome de produto, cobertura, prêmio, disponibilidade Icatu ou recomendação personalizada.

### 4. Prova visual obrigatória nesta etapa

Use browser real na URL da versão nova e registre o **antes/depois** com capturas ou observações específicas em 1440×900, 768×1024, 390×844, 320×568 e zoom 200%. Confira radios, checkboxes, labels, hero, navegação, cards de possibilidades, detalhes recolhidos, impressão e teclado/foco. Teste no navegador pelo menos URL familiar + entender e relato renda + comparar; verifique que a copy pública não contém enums técnicos e que a prova técnica continua acessível. Se a sessão de execução não tiver browser interativo, não afirme aceite: entregue capturas obtidas por ferramenta real disponível ou registre cada lacuna e deixe a URL ativa para a auditoria do patrocinador. Faça inspeção de contraste e de largura sem scroll horizontal.

### 5. Preservar o que já foi comprovado

Não quebre envelope 1.1 e contribuições `USER_DECLARED` / `GOVERNED_SOURCE`, timestamps distintos, idempotência, A/B, URL governada, recusa sem provider, `MOCK_UNAVAILABLE`, nem o princípio SegSense não chamar o mock. Execute frontend lint/test/build, backend `mvnw verify`, testes da Spider/mock tocados e prova HTTP canônica da stack nova após restart seguro pelo ledger. Não reinicie a stack antiga `:5178` sem propriedade comprovada. Se a versão nova não puder ficar no ar ao fim, indique a URL correta e o procedimento seguro de início, sem anunciar prontidão visual.

Copie este prompt integralmente para `segsense/documents/SEGSENSE_PRM_017_COR_001.md`; atualize `SEGSENSE_REV_017`, `SEGSENSE_DEMO_RUN_001`, matriz `SEGSENSE_JRN_EVID_001`, índice e README pertinente, preservando o histórico do PRM_017. Documentos novos com prefixo `SEGSENSE_`. Na devolutiva, mostre: causa CSS e correção; frases antes/depois; capturas por viewport ou lacunas honestas; dois fluxos reais; testes; estado das duas stacks; Git. **Pare para auditoria. Não autoaprove. Não haverá segundo corretivo do PRM_017.**
