# ActionFinance retomada da gestão financeira empresarial

Data: 02/10/2026. Proposta do analista para navegação, jornadas, dados e sequência de evolução. A direção foi autorizada pelo proprietário; este documento não declara funcionalidades implantadas nem encerra o aceite pendente da Spider. Não é um comando de deploy ou de reparo histórico.

## Objetivo e fronteiras

ActionFinance administra direitos, obrigações, recebimentos, pagamentos, contas e posição financeira da empresa. Funciona sem integração e recebe dados de sistemas externos pela Spider. ActionHub Pay é a primeira origem integrada, não o limite do produto. Panne permanece responsável pelo estoque físico e origem de compras.

Receber Pix direto no banco, dinheiro ou pagamento por outro processador deve caber no mesmo domínio. Registrar um pagamento externo realizado não exige executá-lo pelo ActionHub ou Mercado Pago. Eventual execução integrada pelo ActionHub Pay depende de capacidade e contrato específicos; não se pressupõe payout existente. Importação de extrato por arquivo não é um conector bancário; futuros conectores entre sistemas passam pela Spider.

## Base observada e limites da revisão

Foram lidos DOM_001 v0.6, DAT_001 v0.94, UX_001 v0.11 e INT_001 v0.67 em C:\Projetos\ActionFinance\documents. Esta revisão é documental, apoiada nas capturas do proprietário; não substitui auditoria do código ou do banco.

| Base descrita nos documentos | Implicação para a evolução |
|---|---|
| Títulos a receber/a pagar, baixas parciais/totais, estorno do registro | Aproveitar o domínio existente; não criar um segundo controle manual. |
| Contas financeiras e movimentos gerenciais | Preservar a distinção entre saldo gerencial e extrato bancário. |
| Transações Pay e revisões, sem vínculo com título | Projetar associação auditada antes de qualquer geração de baixa. |
| Uma baixa para um título no modelo atual | Rateio e liquidação de vários títulos exigem evolução explícita, não adaptação silenciosa. |
| Identidade e autorização por empresa | Filtros não ampliam autorização; origem não substitui empresa. |

Há divergências temporais nos documentos: DAT ainda diz V13 não publicada, enquanto os relatos posteriores dizem publicada; DOM e INT misturam estados antigos de integração com incrementos novos. A próxima revisão deve reconciliar cada afirmação com migration/código/evidência de implantação. Não copiar o status antigo para a nova especificação nem reescrever pareceres históricos.

## Navegação e sidebar

O menu deve refletir tarefas financeiras. Proposta alvo:

| Grupo | Destinos | Situação do desenho |
|---|---|---|
| Visão geral | Posição e pendências | Futuro, depende de métricas definidas. |
| Recebíveis | A receber; Recebimentos | Títulos existentes; visão de recebimentos a ampliar. |
| Pagáveis | A pagar; Pagamentos | Títulos e baixas existentes; visão de pagamentos a ampliar. |
| Tesouraria | Contas e movimentos; Transferências; Conciliação | Contas existentes; transferências e conciliação propostas. |
| Planejamento | Fluxo de caixa | Proposto. |
| Cadastros | Clientes e fornecedores; Categorias; Centros de custo | Dois primeiros existentes; centros de custo propostos. |
| Integrações | Conexões; Sincronizações; Pendências de importação | Organizar capacidades atuais e evoluir conforme entrega. |

Não publicar destinos vazios. O menu inicial apresenta apenas jornadas disponíveis, agrupadas de modo coerente. “Recebimentos do Pay” deixa de ser o conceito principal; Pay é origem/conexão dentro da gestão de recebimentos. Rotas existentes devem continuar acessíveis por redirecionamento ou compatibilidade ao mudar navegação.

Sidebar: preservar logo compacta e tamanho aprovado, base navy, destaque ouro e branco; grupos legíveis, ícones acompanhados de texto, seleção inequívoca e área de conteúdo mais útil. Reduzir espaços sem função e evitar um seletor de empresa ocupando quase todo o cabeçalho. Nome longo deve continuar acessível. Mobile com drawer, teclado, foco e proteção de rascunho preservados. Refinamento visual posterior deve ser avaliado em telas preenchidas, vazias, com falha e com nomes longos.

“Empresa autorizada · ambiente PRODUCTION” sai do conteúdo operacional. Empresa aparece no contexto global. Na integração pode constar “Conectado ao ActionHub Pay”. Configuração técnica de ambiente fica em detalhes de conexão; não alterar o contrato ao retirar a palavra da tela. Dados de teste continuam claramente identificados e separados. Conexão de produção e comprovação do pagamento individual são dimensões diferentes.

## Jornada de recebimentos

Entrada principal: Recebimentos. A lista reúne registros financeiros locais e observações externas identificadas, preservando seu tipo. Uma observação externa não se torna recebimento confirmado apenas por aparecer na mesma área.

1. Usuário seleciona empresa e período, com tipo de data explícito: cobrança, pagamento ou registro/importação. Ausência de data não recebe substituição silenciosa.
2. Pode filtrar estabelecimento, origem comercial, sistema de origem, processador, método, conta, cliente, situação e pendência. Oferecer apenas dimensões disponíveis, sem inventar estabelecimento com base em app_id.
3. Abre um registro reconhecível por pedido/referência curta, contraparte quando disponível, valor e data; UUID completo fica no detalhe com copiar.
4. Detalhe separa cobrança, pagamento informado, disponibilização, vínculo financeiro e conciliação. Mostra origem e data de cada informação relevante.
5. Pendência informa o dado faltante e a ação possível: atualizar origem, consultar evidência ou corrigir vínculo gerencial. Não oferecer “aprovar como real” para substituir evidência ausente.
6. Recebimento externo já realizado pode ser registrado manualmente pela jornada existente de título e baixa. Recebimento avulso sem título depende de decisão de modelo; não criar obrigação fictícia automaticamente.
7. Uma integração posterior pode encontrar algo já lançado manualmente. Sugerir vínculo com comparação dos dados; nunca registrar outra baixa ou fundir por valor/data apenas.

Filtros de origem devem separar: empresa administrada; estabelecimento/unidade; canal de venda; sistema ActionHub; processador Mercado Pago; método Pix. São conceitos independentes. A visão de toda a empresa inclui contas e origens externas autorizadas. Não pressupor consolidação entre empresas nesta entrega.

Resumo: separar resultado da última sincronização de estoque atual de pendências. Exemplo de texto, sem números fictícios no produto: “Sincronização concluída” e “Registros que precisam de revisão”. Totais cobrado/pago/líquido usam definições distintas, informam registros excluídos ou sem valor e não somam moedas diferentes. Aprovado na origem não significa conciliado nem disponível no banco.

## Inventário completo das informações

“Todos os dados da transação” significa inventariar todos os campos financeiros e operacionais pertinentes, com justificativa explícita para ausência ou exclusão. Não significa copiar segredos, credenciais, cartão completo ou payload pessoal indiscriminado para logs/Monitor.

| Grupo | Campos a investigar na origem e contrato |
|---|---|
| Identidades | Pedido, tentativa, cobrança, transação do processador, referência comercial e vínculo de empresa/app/unidade. |
| Participantes | Cliente/fornecedor, identificadores na origem e identificação mínima necessária ao operador. |
| Origem | Sistema, aplicação, canal, estabelecimento, processador e método. |
| Valores | Moeda, cobrado, pago, desconto, juros, multa, tarifa, devolução, líquido e disponibilizado. |
| Datas | Criação, vencimento, aprovação, pagamento, disponibilidade, devolução e atualização da fonte. |
| Destino | Conta de recebimento ou identificador do destinatário, sem expor credenciais bancárias. |
| Estados | Situação original, tradução de negócio, captura, cancelamento, reembolso parcial/total e evidência de teste/operação. |
| Rastreio | Fonte, campo de origem, momento da observação, revisão, execução Spider e execução de persistência AF. |

Para cada campo entregar: definição, fonte concreta, tipo/unidade, nulabilidade, autoridade, disponibilidade histórica, passagem pelo Hub/Spider/AF, apresentação e tratamento de ausência. Classificar “existe e é transmitido”, “existe mas não é transmitido”, “recuperável por consulta autorizada”, “não registrado” ou “não aplicável”. Uma consulta histórica somente leitura não autoriza APPLY. O preço atual de R$70 não preenche nenhum campo ausente.

## Modelo conceitual proposto

Os nomes abaixo são conceitos, não instrução para criar tabelas agora.

| Conceito | Relação e responsabilidade |
|---|---|
| Empresa e unidade | Empresa isola autorização/dados; unidade opcional organiza operações dentro da empresa. |
| Contraparte e identidade externa | Uma contraparte pode ter referências em diferentes sistemas; associação explícita e auditada. |
| Título | Direito/obrigação com valor, moeda, competência e vencimento; independente da forma de pagamento. |
| Liquidação e alocação | Registro financeiro relacionado a título(s) por valor; evolução além do vínculo único atual requer regras próprias. |
| Conta e movimento | Conta gerencial recebe movimentos de liquidação, abertura, reversão e futuras transferências/tarifas. |
| Transação externa e observação | Identidade estável por empresa, conexão, origem e ID; observações versionadas não sobrescrevem fatos locais. |
| Vínculo financeiro | Liga transação externa a liquidação/título existente, com valores alocados, autoria e motivo; previne duplicação. |
| Extrato e linha | Evidência bancária importada com identidade da conta, período, arquivo/origem e deduplicação. |
| Conciliação e alocações | Liga linhas do extrato a movimentos; suporta futura correspondência parcial ou agrupada sem exceder valores disponíveis. |
| Transferência | Duas pernas correlacionadas entre contas próprias; tarifa separada; não receita/despesa. |
| Projeção | Derivada de títulos pendentes e hipóteses identificadas; separada dos movimentos realizados. |

Invariantes: escopo de empresa em todos os vínculos; centavos inteiros e moeda explícita; nulo diferente de zero; datas financeiras distintas de timestamps de integração; IDs de pedido e processador distintos; idempotência e controle de concorrência; correções/reversões auditadas; nenhuma exclusão do fato original para “corrigir” saldo. Conciliação não cria uma segunda entrada para o mesmo recebimento. Recebimento bruto, tarifa e repasse líquido precisam de um modelo explícito de conta intermediária antes de gerar movimentos: uma cobrança de cartão não equivale necessariamente a um depósito bancário.

## Conciliação e fluxo de caixa

Primeiro recorte proposto de conciliação: importação de extrato por arquivo escolhido a partir dos bancos efetivamente usados, prévia validada, conta e período explícitos, rejeições por linha e detecção de reimportação. Sugestões de correspondência não são aceite automático. Usuário confirma vínculos; desfazer conciliação preserva trilha e não estorna dinheiro. Diferenças ficam pendentes, sem ajuste de saldo inventado.

Fluxo realizado parte de movimentos válidos por conta e data efetiva. Fluxo projetado parte de saldos gerenciais identificados e valores restantes de títulos por vencimento; excluir parcelas já liquidadas evita contagem dupla. Transferências internas se anulam na consolidação das contas participantes, mas aparecem em cada conta. Separar saldo gerencial, saldo do extrato e diferença ainda não conciliada. Previsão não é saldo bancário nem lucro.

## Sequência de entregas e critérios

| Recorte | Entrega verificável | Limite |
|---|---|---|
| 1. Especificação e inventário | Dicionário campo a campo, mapa de fontes, lacunas e comparação com modelo atual; wireframes de sidebar, lista e detalhe. | Sem migration/deploy nesta etapa documental. |
| 2. Recebimentos organizados | Filtros reais, origem reconhecível, detalhe completo disponível, pendências acionáveis e navegação coerente. | Importação não gera baixa. |
| 3. Controle unificado | Jornada manual preservada, pagamentos/recebimentos listáveis, associação externa com prevenção de duplicação. | Vínculos e movimentos só após regras explícitas e testes. |
| 4. Tesouraria e conciliação | Transferências, extrato importado, correspondência confirmada e divergências. | Sem iniciar transferências bancárias. |
| 5. Fluxo de caixa | Visões realizada/projetada com origem verificável e sem contagem dupla. | Não é contabilidade fiscal ou lucro. |

No próximo prompt de execução documental, o Cursor deve confrontar este desenho com código/migrations/contratos e devolver gaps concretos, sem implementar todas as frentes. O analista define UX e avalia os artefatos; o proprietário decide prioridades e aceita o produto. A autorização para retomar o projeto não encerra falhas nem autoriza custos novos.

## Critérios para a primeira revisão

- Operador encontra apenas registros da origem comercial desejada sem confundir app, empresa e processador.
- Recebimento manual fora do ActionHub tem lugar claro na navegação e mantém a jornada já existente.
- Dados faltantes aparecem como ausentes, com motivo e ação possível; nenhum valor é presumido.
- Cabeçalhos e status usam linguagem financeira; diagnóstico técnico fica acessível em rastreio.
- Lista e detalhe distinguem observação externa, liquidação local e conciliação; nenhum total duplica o mesmo fato.
- Modelo e migrações propostas demonstram isolamento, concorrência, deduplicação e trilha de correção antes de implementação.
- Cenários de uso cobrem desktop/mobile, teclado, nomes longos, filtro sem resultados, resposta atrasada, ausência de informação e acesso revogado.

Pendências de Spider, canónica histórica, regressão Pay, APPLY histórico e PRM_007 continuam separadas. Nenhum PRM de implementação é emitido por este documento.
