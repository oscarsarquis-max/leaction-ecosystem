# Prompt 023 — Tesouraria e análise financeira empresarial

Baseline AF-BL-023, revisão 1.2, de 15/10/2026. Documento completo e independente para o Cursor. Preservar integralmente as revisões 1.0 e 1.1. A revisão de requisitos não é a versão do produto; aplicar as regras de versionamento do Prompt 024.

Orientação de execução armazenada em 15/10/2026. As revisões 1.0 e 1.1 permanecem nos arquivos próprios. O mapa, o dicionário, as fórmulas e o plano da primeira fatia estão no projeto e no plano desta revisão, não neste arquivo.

## Objetivo e decisões do proprietário

Transformar o Finance em plataforma de gestão e análise financeira, com informação suficiente para decidir o que pagar, acompanhar o que entra, identificar diferenças e antecipar falta de caixa. Não entregar apenas um extrato com valores nem gráficos sem composição verificável.

Toda a movimentação financeira permanece, por enquanto, no Mercado Pago, incluindo recebimentos e despesas. Loja de Pães, iniciativas Inove4us e SegSense pertencem à mesma empresa titular. Tratá-las como iniciativas/unidades de negócio, não como empresas independentes. O saldo da conta pertence à empresa; sua atribuição gerencial às iniciativas não cria saldos bancários separados.

Nesta etapa, pagamentos são executados no MP e registrados/conciliados no Finance. Não implementar execução automática de pagamentos, estornos ou transferências. A arquitetura deve admitir outras contas e meios no futuro, sem limitar o modelo ao MP.

O padrão para despesas compartilhadas é “Não atribuída” até classificação. Rateio percentual só mediante regra registrada, com autor, vigência e histórico. Não inferir categoria ou iniciativa somente pelo favorecido. Não perguntar novamente se as iniciativas pertencem à mesma empresa.

## Ponto de retomada e sequência de entrega

O executor relatou a publicação do produto 0.1.1 no incremento 027, com enriquecimento do adapter e preservação das requisições 1.3/1.4. A captura do proprietário mostra 12 registros armazenados, 10 pendências, 1 criado e 11 atualizados. Esses números são evidência daquele instante, não constantes do produto. O acabamento visual foi encaminhado no Prompt 028.

Concluir as provas pendentes do 027 e o acabamento do 028 sem refazer o que já foi entregue. Em seguida, avançar nas fatias:

1. Extrato da conta MP, identidade dos movimentos e vínculo com recebimentos existentes.
2. Categorização, origem, atribuição às iniciativas e conciliação.
3. Posição de caixa, compromissos e filtros integrados à análise.
4. Fluxo realizado/projetado e gráficos de gestão com composição verificável.

Inspeção e preparação do projeto podem avançar enquanto o acabamento é concluído. Não iniciar outro ciclo genérico de levantamento. Reutilizar criticamente a proposta de contratos 026 e produzir diferenças concretas para o próximo incremento executável.

## Arquitetura e proteção contra regressões

Toda integração Finance–Hub passa pela Spider. Não criar fallback Finance → Hub ou Finance → MP. A integração da Loja com os planos do Hub é outro percurso e deve permanecer intacta.

A autorização dada no 027 para modificar o adapter foi específica para enriquecer a observação de cobrança. Ela não autoriza novas capacidades, mudanças no núcleo ou novas alterações de infraestrutura da Spider. Preservar essa entrega; não reverter o adapter sob a antiga proibição geral da revisão 1.1.

Para extrato, posição ou outros fatos, verificar capacidades já existentes e apresentar eventual evolução necessária com contratos, consumidores afetados, compatibilidade, testes e rollback. Novas alterações da Spider exigem autorização delimitada; não bloqueiam o projeto financeiro independente.

Manter observação de cobrança, movimento de conta, posição e obrigações como conceitos distintos. Não transformar a lista de pagamentos em extrato completo nem presumir que o Monitor prove o commit no Finance. Não publicar dados sintéticos em produção.

## Conta, empresa e iniciativas

Confirmar a correspondência técnica entre a conta MP, o titular e a empresa Finance atualmente exibida como Loja de Pães. Não renomear empresa nem mover vínculos de acesso automaticamente. O nome atual no seletor não justifica atribuir todas as operações à iniciativa Loja.

Projetar empresa → contas financeiras e empresa → iniciativas, permitindo uma conta atender várias iniciativas. Identificar aplicação comercial, produto/plano e pedido independentemente da origem técnica ActionHub Pay. Preservar códigos externos e manter nomes de apresentação amigáveis.

Separar pagador, cliente comercial, fornecedor/favorecido e titular da conta. Identificador técnico de checkout, como o endereço interno observado em amount.hub.local, não deve ser promovido a cliente identificado. Não deduzir pessoa, documento ou contato a partir de token.

## Informações completas e proveniência

Entregar dicionário de dados por tipo de fato, indicando significado financeiro, fonte, obrigatoriedade, precisão, possibilidade de ausência e uso analítico. Não exigir campos inaplicáveis a todo evento nem permitir “Não informado” sem diagnóstico e tratamento.

Cobrir, conforme o fato: identidades; contexto; valores sustentados pela fonte; datas sem troca de significado; estados em dimensões distintas; rastreabilidade.

Distinguir não aplicável, não coletado, indisponível na fonte, não transportado e ainda não classificado. Para cada lacuna relevante, indicar ação de resolução e seu efeito nos indicadores. Não confundir ausência com zero. Usar moeda e precisão explícitas; não somar moedas diferentes sem regra cambial declarada.

Valores pagos não derivam de cobrado nem de um rótulo de aprovação. PRODUCTION no envelope não comprova natureza real do pagamento. Evidência de ambiente, identidade comercial e disponibilidade financeira são questões separadas.

## Categorização, extrato, posição, filtros e indicadores

O prompt de 15/10/2026 define hierarquia de categorias, rateio com soma exata, extrato com deduplicação por identidade estável, conciliação confirmada pelo operador, três posições de caixa, filtros do mesmo recorte em lista, totais e gráficos, e seis instrumentos de gestão com fórmula, cobertura e composição. A projeção inicial é determinística. Não há IA preditiva, execução de pagamento, estorno ou transferência pelo Finance.

A interface mantém a identidade visual aprovada e duas barras horizontais. Telas novas só entram na navegação com jornada funcional. Prévia visual usa exemplos sintéticos identificados. Em produção, esses exemplos não substituem evidência real.

## Trabalho imediato

Esta revisão consolida requisitos e determina preparar a próxima fatia executável, aproveitando 026/027/028. Não reabrir decisões já confirmadas.

As autorizações dos incrementos 027 e 028 permanecem nos seus limites. Esta revisão não autoriza por si só novas mudanças da Spider, execução de pagamentos, importação financeira produtiva, alteração de saldo inicial ou nova infraestrutura paga.

Entregas pedidas: `ACTIONFINANCE_PROJETO_TESOURARIA_MP_023_R1_2.md` e `ACTIONFINANCE_PLANO_ENTREGA_TESOURARIA_023_R1_2.md`. Separar implementado, publicado, provado e aceito. Não atribuir aceite ao proprietário.
