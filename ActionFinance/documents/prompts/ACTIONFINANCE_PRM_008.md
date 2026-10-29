# ACTIONFINANCE_PRM_008 — Primeira integração via Spider: prova controlada com ActionHub Pay

Data: 30/09/2026. Analista de negócio, TI e UX → Cursor, único desenvolvedor.

## 1. Objetivo e critério central

Construir uma primeira fatia verificável de integração **ActionFinance → Spider → ActionHub Pay → Spider → ActionFinance**, em ambiente isolado/homologação. O proprietário definiu essa integração como prova da viabilidade da Spider. Não basta três serviços responderem health: a Spider precisa receber uma intenção autorizada, selecionar/acionar a capacidade do Pay pelo seu modelo arquitetural, acompanhar o resultado e devolvê-lo com correlação e isolamento.

**Sem comunicação direta AF↔Pay, inclusive para consulta de status, eventos, conciliação do resultado ou recuperação de falha.** A credencial do Pay não pertence ao ActionFinance. Nenhum bypass temporário para produzir uma demonstração verde. Se faltar capacidade da Spider, implementá-la de forma versionada e compatível, ou declarar precisamente a lacuna.

Primeiro cenário: consultar e acompanhar um pagamento de teste da Loja de Pães. Acrescentar solicitação de pagamento **somente em sandbox sem movimentação real**, quando o Pay oferecer capacidade comprovada para isso. Incluir consulta de recebimentos na matriz e no adaptador quando existir contrato documentado. Não inventar que o Pay já executa pagamentos de saída apenas porque o produto tem esse nome.

Não desenvolver toda a tesouraria, todos os conectores ou um novo PSP. ActionHub Pay conserva sua essência e executa pagamentos; ActionFinance gerencia obrigações e resultados. Panne origina compras e mantém estoque físico. A integração do Panne fica para recorte posterior; este ciclo já deve comportar referência de origem sem ser hardcode da loja.

## 2. Situação do PRM_007 e limites de ativação

O proprietário confirmou login humano e correção visual do nome. O arquivo `documents/reviews/screenshots/prm-007-encerramento/logout-csrf-log.json` comprova sessão 200, recusa sem CSRF e com token inválido, sessão preservada e logout válido/replay 401.

O último relatório lido pelo analista ainda não contém conclusão do restore real e limpeza. Antes de reportar encerramento do PRM_007, reconciliar o estado com os resultados atuais do executor: se terminou, anexar evidências de restore e remoção dos recursos temporários; se ainda está em execução, registrar pendência com precisão. Não reiniciar restore já em andamento ou pedir novo login sem necessidade. Não marcar o ciclo aprovado em nome do analista.

A preparação e a prova isolada deste PRM_008 podem avançar enquanto se resolve o fechamento operacional. **Nenhuma ativação de integração em produção**, pagamento real, mudança de infraestrutura compartilhada ou novo gasto AWS está autorizado por este prompt. A publicação do produto autônomo permanece separada da ativação do conector.

## 3. Levantamento factual obrigatório, curto e orientado a implementação

Ler instruções aplicáveis e identificar o trabalho existente no monorepo antes de editar. Não sobrescrever alterações paralelas. Paths conhecidos: `C:\Projetos\ActionFinance`, `C:\Projetos\spider`; a documentação do monorepo aponta `leaction-platform/` como ActionHub — confirmar onde vive o módulo Pay e seu estado atual.

Entregar matriz compacta de capacidades: recebimento, pagamento de saída, consulta por ID/referência, estados finais/intermediários, cancelamento/estorno, idempotência, consulta após timeout e eventos. Para cada uma: endpoint/código/schema real, autenticação, escopo de empresa, comportamento e ambiente de teste. Distinguir existe/proposto/ausente. Não extrair segredos ou acessar registros financeiros reais para preencher a matriz.

Revalidar lacunas conhecidas da Spider: schema 1.2 só seguro/crédito e SYNC; EXPERIENCE não executa capability; registry; idempotência em memória. Documentação anterior aponta PRM_005/006 como gates futuros de integração, mas esses IDs já foram usados para outros escopos: corrigir referências obsoletas sem reescrever o histórico.

A decisão sobre a fatia demonstrável depende dessa matriz. Não parar só no levantamento se houver contrato utilizável. Se pagamento de saída não existir no Pay, entregar consulta/recebimentos reais disponíveis via Spider e uma lista precisa do trabalho faltante; não implementar um motor de pagamentos novo disfarçado de adaptador.

## 4. Evolução da Spider e fronteiras de código

Este ciclo autoriza mudanças locais necessárias no ActionFinance e na Spider, além de adaptação mínima de borda no módulo Pay identificado. Registrar caminhos e motivos. Não alterar Panne, módulos de assinaturas/vendas ou fluxos produtivos alheios.

- ActionFinance continua EXPERIENCE: declara intenção e acompanha. Não remover genericamente a proibição de EXECUTE_CAPABILITY/CAPABILITY_RESULT do EXPERIENCE. A execução pertence à orquestração da Spider e à borda PROVIDER apropriada.
- Criar evolução explícita de contrato financeiro e capacidade de consulta/solicitação, conforme o padrão efetivo da Spider. Escolher versão após conferir as existentes; não reutilizar propósito de seguro/crédito nem colocar payload clandestino em extensions fechadas.
- Registro e seleção da capacidade devem ocorrer nos mecanismos da Spider. Não criar apenas um proxy com URL Pay fixa sob um endpoint novo e chamá-lo de prova de orquestração.
- Preservar compatibilidade dos contratos e testes de SegSense/SpiderBank. Registrar manifesto e configuração de ambiente de teste, sem alegar certificação de satélite por configuração local.
- Credenciais de serviço separadas da sessão humana; autorização de empresa verificada nos limites AF, Spider e Pay. Empresa do payload precisa estar vinculada ao chamador autorizado, não aceita por confiança em um header.
- Persistência própria para estado de integração, correlação e deduplicação onde necessária. Não usar banco do AF para guardar estado interno da Spider nem mudar toda sua arquitetura de persistência sem necessidade. Não tratar store em RAM como garantia durável financeira.
- Retorno assíncrono deve ter contrato, autenticação, validação, deduplicação e roteamento reais. Se a capacidade só permitir polling, fazê-lo AF→Spider→Pay com limites/backoff, mantendo o papel de cada componente. Não inventar webhook ou prometer entrega assíncrona inexistente.

## 5. Dados e invariantes do ActionFinance

Entregar modelo físico das entidades efetivamente necessárias e novas migrations incrementais; não alterar V1–V7 ou outras migrations já aplicadas. Atualizar DAT com campos/tipos/PK/FK/índices/retenção e diagrama relacionando títulos, operações externas, referências Pay e mensagens processadas.

Requisitos mínimos:

- Mapeamento explícito e autorizado de tenant/empresa local para empresa/conta no Pay. Nada de inferir pelo nome, CNPJ ausente ou domínio do operador.
- Operação externa com UUID próprio, tenant/empresa, tipo/capacidade, origem, referência do título quando aplicável, valor/moeda, estado externo, estado de entrega, chave de idempotência estável, fingerprint semântico, correlationId, referência Spider/Pay e timestamps. Manter dinheiro em unidades menores e contrato de precisão já usado.
- Unicidade por origem/empresa/ID externo e deduplicação de eventos no escopo correto. Mesmo ID externo em empresas distintas não autoriza acesso cruzado. Mesma chave e conteúdo diferente é conflito.
- Outbox/inbox ou mecanismo durável equivalente onde houver mensagens e efeitos locais. Descrever limites transacionais entre serviços; não alegar exactly-once distribuído. Retry após resposta perdida reutiliza identidade da mesma operação, nunca cria novo pagamento por mera dúvida.
- Evento atrasado ou duplicado não regride pagamento confirmado nem gera nova baixa. Divergência de estado/valor/moeda/empresa vai para revisão, não é ajustada silenciosamente.
- HTTP 200/202 ou “solicitação aceita” não é liquidação. Timeout pode significar resultado desconhecido, não falha definitiva. Registrar evidência de confirmação do Pay antes de qualquer efeito financeiro.
- Neste primeiro recorte, resultados externos são registrados para acompanhamento e **não geram baixa automática em títulos reais**. Se mostrar vínculo com título de teste, manter explícito que o efeito financeiro automático ainda não está habilitado. Não misturar importação com execução.
- Impedir nova solicitação para a mesma obrigação quando já há operação pendente/desconhecida que pode ter sido executada; oferecer consulta/reconciliação do resultado pelo caminho Spider.
- Retentativa exige autorização atual; replay não contorna revogação. Históricos não contêm tokens, dados bancários completos ou payloads sensíveis desnecessários.

## 6. UX da fatia de homologação

Preservar layout/cores/logos. Não habilitar botões vazios em produção. Ativar a experiência somente por configuração de integração do ambiente isolado.

No detalhe de título de teste ou área de acompanhamento coerente com a navegação existente:

- Mostrar origem, referência externa, valor, estado, última atualização e resultado da consulta. Separar “registro no controle” de “execução externa”.
- Identificar claramente **Homologação — sem movimentação real** em qualquer solicitação de sandbox. Essa indicação não substitui configuração que realmente impeça execução real.
- Ação de consulta é “Consultar no ActionHub Pay”; percurso técnico pela Spider fica nos detalhes de rastreio, sem jargão no fluxo principal.
- Estados legíveis: aguardando envio, solicitação aceita, em processamento, confirmado pelo Pay, recusado, resultado desconhecido e requer revisão, conforme estados de fato suportados. Não criar estados finais presumidos.
- Após resposta perdida, oferecer “Consultar resultado”/repetição da mesma operação quando segura. Não apresentar botão que emita nova ordem com nova chave.
- Se existir solicitação sandbox: resumo de revisão com empresa, obrigação, valor e destino de teste, ação explícita e bloqueio de clique duplicado. Leitor não solicita execução.
- Spider indisponível: mensagem clara e pendência preservada. Nenhum fallback direto ao Pay.
- Provar desktop 1280 e mobile 360, foco/teclado, nomes longos e ausência de overflow. Sem novo redesenho geral.

## 7. Prova da viabilidade da Spider

Executar componentes reais AF e Spider e adaptador do Pay. Preferir sandbox real do módulo Pay. Se ele não tiver ambiente/capacidade disponível, usar simulador apenas na borda externa do provider, explicitamente identificado, e declarar o alcance limitado: **contrato/orquestração provados; integração real com Pay ainda não comprovada**. Mock não recebe aceite de viabilidade ponta a ponta com Pay.

Entregar evidências ligadas por correlationId, sem dados secretos, para:

1. Intenção AF autenticada → validação/roteamento Spider → capacidade Pay → retorno Spider → atualização do acompanhamento AF.
2. Repetição idêntica, concorrência e reuso de chave com corpo diferente; contagem do efeito no provider de teste.
3. Pay aceita a solicitação mas a resposta se perde; repetir/consultar sem duplicar execução. Se o Pay não oferece meios seguros para resolver isso, declarar execução bloqueada e manter apenas consulta.
4. Reinício da Spider e do AF durante pendência sem perda da identidade/deduplicação; restart do Pay conforme capacidade do ambiente de teste.
5. Eventos duplicados, fora de ordem, inválidos e de empresa errada; nenhum efeito financeiro ou vazamento indevido.
6. Spider fora do ar impede o acesso ao Pay pelo AF. Demonstrar configuração/controle de rede de teste ou instrumentação que comprove ausência de chamadas diretas, não apenas um diagrama.
7. Usuário sem permissão, vínculo revogado e tentativa de trocar empresa são recusados antes de executar ou devolver replay.
8. Contratos antigos continuam funcionando e a operação manual do AF continua independente da Spider.

Não usar transferência real de pequeno valor como teste. Nenhum envio real de dinheiro, cobrança, convite ou notificação a cliente faz parte deste prompt.

## 8. Entregáveis e retorno

Salvar este prompt integral em `documents/prompts/ACTIONFINANCE_PRM_008.md`. Relatório `documents/reviews/ACTIONFINANCE_REV_008.md`. Atualizar INT/DOM/DAT/UX e a documentação Spider/Pay estritamente relacionada, com estado factual.

Retorno deve trazer:

- Situação residual do PRM_007, sem autoaceite e sem misturar as provas.
- Matriz de capacidades e diferenças entre arquitetura alvo e código atual.
- Versões/contratos alterados, manifesto/capacidade, componentes e dados físicos.
- Como executar a fatia isolada, UX demonstrada e caminho completo de correlação.
- Testes e limitações; distinguir serviço real, sandbox, simulador e parte não implementada.
- Parecer técnico do executor sobre o que a prova demonstrou da Spider e quais lacunas ainda impedem execução real segura. Não declarar inviabilidade ou sucesso geral a partir de um único happy path.

Sem deploy de integração em produção, commit/push ou PRM_009. Devolver para revisão do analista. O resultado procurado é uma fatia funcionando com limites explícitos, não apenas um novo documento de arquitetura nem uma integração direta renomeada como Spider.
