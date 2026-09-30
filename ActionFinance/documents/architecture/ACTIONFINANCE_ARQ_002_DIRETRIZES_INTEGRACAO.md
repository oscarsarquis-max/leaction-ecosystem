# ACTIONFINANCE_ARQ_002 — Incorporação das diretrizes de integração

Data: 28/09/2026 · Natureza: atualização arquitetural, não prompt de implementação.

Fonte: “Diretrizes de integração — ActionFinance, Spider e ActionHub Pay”, fornecida pelo proprietário em 28/09/2026, preservada integralmente em `ACTIONFINANCE_DIR_INT_001_2026-09-28.md`.

## 1. Precedência e decisões atualizadas

As diretrizes mais recentes prevalecem sobre os trechos conflitantes da arquitetura v0.2 e dos ADRs anteriores. O histórico não será apagado ou apresentado como se sempre tivesse adotado a decisão nova.

| Tema | Decisão anterior | Diretriz vigente |
|---|---|---|
| ActionHub | Limitado ao recebimento de assinaturas | ActionHub Pay permanece módulo do Hub e executa as capacidades financeiras existentes e confirmadas, incluindo cobranças/PIX; não presumir pagamento a fornecedores ou outra capacidade ausente |
| Caminho novo | Providers financeiros ainda a definir | ActionFinance → Spider → porta/adapter ActionHub Pay → contrato técnico confirmado |
| Endereço ActionFinance | Publicação planejada em finaction.com.br | Identidade/endereço previsto: actionfinance.actionhub.com.br |
| Domínio registrado | finaction.com.br confirmado pelo proprietário | Continua registrado; finalidade futura, alias ou redirecionamento não definidos. Não implica renomear o produto |
| Endereço ActionHub Pay | Sem decisão específica de subdomínio | Mantém actionhub.com.br. Não criar pay.actionhub.com.br |
| Consumidores existentes | Divergência de cobrança avulsa registrada | Preservar loja/PIX, contratos e webhooks existentes. A existência dessas operações não autoriza migrá-las |
| Entrega de estado | Canal futuro a definir | Preferência inicial por consulta do BFF à Spider, somente quando houver contrato real de consulta |

Registro de domínio, escolha de hostname e DNS/TLS publicado são fatos distintos. Nenhuma configuração de DNS, certificado, CORS, infraestrutura ou publicação foi realizada por esta incorporação.

Namespace Spider indicado pelo proprietário: spider.actionhub.com.br, monitor.spider.actionhub.com.br, api.spider.actionhub.com.br e callbacks.spider.actionhub.com.br. Não inferir que esses destinos estejam acessíveis ou prontos para uso apenas por constarem na diretriz.

## 2. Responsabilidades preservadas

- ActionFinance mantém backend Java na versão da Spider, PostgreSQL próprio e módulos de gestão financeira definidos anteriormente: obrigações, recebíveis, caixa, conciliação financeira, custos/resultados e planejamento conforme futuras entregas.
- O papel EXPERIENCE rege sua participação no ecossistema. Não reduz automaticamente o produto a um BFF sem domínio ou banco.
- Cadastrar obrigação local não executa pagamento. A execução externa é governada pela Spider e realizada pelo ActionHub Pay para operações que seu contrato realmente suportar.
- Panne continua proprietário do estoque físico da padaria. Integrações financeiras não transferem esse estoque ao ActionFinance.
- Operações locais mantêm autorização/auditoria próprias; não ganham IDs de execução Spider fictícios. A exigência de Monitor aplica-se às operações de integração efetivamente processadas pela Spider. Eventual telemetria de cadastro local exige contrato próprio, sem simular execução.
- Não implementar papel PROVIDER no ActionFinance para contornar limites do EXPERIENCE.

## 3. Restrições obrigatórias incorporadas

Frontend → backend ActionFinance → Spider. Nenhum cliente direto ActionFinance → ActionHub/banco/PSP e nenhum webhook ActionHub → ActionFinance.

A Spider chama uma fronteira técnica versionada do ActionHub Pay, autenticada para a Spider, sem depender de sessão de usuário ou reusar credencial da loja. O caminho HTTP será confirmado por inspeção e contrato; não definido aqui.

Separar ingresso de solicitação e execução interna no Hub para impedir recursão: o adapter não pode chamar um endpoint que devolva a mesma solicitação à Spider. Esse limite exige evidência e teste quando implementado.

Idempotência e correlação atravessam componentes, com persistência e fingerprints semânticos, incluindo empresa e valores quando aplicáveis. Duplicidade concorrente não pode produzir nova operação. Chaves derivadas no provider devem ser estáveis, documentadas e vinculadas à intenção original.

Estado gerencial de obrigação, estado técnico de execução e resultado financeiro externo são distintos. HTTP 200/202 ou aceite não provam liquidação. Timeout após possível envio mantém incerteza: consulta governada ou UNKNOWN, nunca retry cego.

Callbacks autenticados/versionados exigem inbox/deduplicação antes do efeito, proteção contra replay, correlação, ordem e conflito. Não aceitar corpo não autenticado como substituto do conteúdo assinado. Persistir espera/correlação de modo que callback antecipado também seja tratado; o diagrama conceitual não autoriza perder retorno que chegue antes da gravação da espera.

Toda evidência deve minimizar dados. Monitor mostra caminho real e projeção permitida, não payload financeiro integral, token, conta ou documento completo.

## 4. Pontos técnicos que continuam exigindo validação

1. O identificador `ACTIONFINANCE` na diretriz é lógico/proposto. A inspeção anterior do schema exigia `satelliteId` minúsculo; manter candidato técnico `actionfinance` e rótulo ACTIONFINANCE até revalidar registry/schema. Não publicar envelope incompatível.
2. A enumeração de capabilities na diretriz é conceitual. Cobrança/recebimento não comprova suporte a transferência, pagamento de fornecedor, devolução, cancelamento ou comprovante.
3. Contrato de satélite financeiro, porta, adapter, contrato interno Hub e callback precisam ser explícitos. Não usar finalidade de seguros/crédito, metadata livre ou endpoint de frontend como atalho.
4. A consulta legada de cobrança encontrada anteriormente pode fazer refresh/fulfillment. Não classificar automaticamente todo GET como leitura pura segura para repetição; revalidar efeitos.
5. Polling do ActionFinance à Spider não cria o ingresso Hub → Spider nem assegura que o estado retornado esteja atualizado. É necessário definir de onde a Spider obtém estado, sua data e o tratamento de indisponibilidade. Sem ingresso/consulta upstream real, não afirmar jornada assíncrona completa.
6. Uma única task com armazenamento em memória não fornece durabilidade nem protege contra duplicação após reinício. Testes financeiros simulados devem declarar essa limitação; conformidade plena exige a persistência definida nas diretrizes.
7. `executionId` só existe quando a Spider realmente cria execução; não inventá-lo para uma interação ou cadastro local.

## 5. Estado do sandbox informado pelo proprietário

Informações recebidas em 28/09/2026, **não revalidadas por inspeção de infraestrutura neste ciclo**: sandbox demonstrável, persistência em memória, uma task ECS, Context Plane desligado, ingresso externo de callback não publicável, ausência de IdP corporativo e Monitor protegido por allowlist.

Preservar esses limites em propostas. Allowlist não substitui autenticação/autorização. MOCK_ONLY não pode esconder falta de durabilidade ou integração. Sem dinheiro real, migração dos consumidores atuais, CAP-021, piloto ou produção autorizados.

## 6. Efeito no ciclo atual

O único prompt em andamento continua **ACTIONFINANCE_PRM_002_COR_001**. Esta diretriz não é seu retorno, não encerra seus gates e não autoriza novo prompt.

O corretivo permanece local: compatibilidade de dependências, testes, restauração, scripts, segurança e frontend mínimo. Não incluir adapter ActionHub Pay, evolução Spider, polling, callbacks, DNS ou qualquer execução financeira nele.

Depois do retorno e revisão do corretivo, os prompts posteriores deverão usar estas diretrizes. Antes da etapa de integração, produzir inventário atualizado e contratos compatíveis nos três sistemas; não ampliar escopo da fundação para antecipar integração.

## 7. Documentos afetados e rastreabilidade

ARQ_001 e ADR-008 devem ser lidos com a atualização de responsabilidade do ActionHub Pay desta nota. INT_001 e ADR-009 continuam identificando lacunas reais; não passam a declarar integração disponível. DOMINIO_001 conserva o fato de registro de finaction.com.br, mas o endereço de publicação planejado é substituído pela diretriz atual.

Esta nota e a fonte integral são a referência vigente para os pontos acima; revisões futuras dos documentos detalhados devem citar essa precedência, preservando histórico e separando decisão de negócio de suporte implementado.
