# ActionFinance reformulação de clientes e fornecedores

Identificador: ACTIONFINANCE_PROMPT_REFORMULACAO_CADASTROS_011. Data: 05/10/2026. Documento novo e independente destinado ao Cursor; não é renumeração do PRM de integração. Não modificar prompts anteriores.

## Mandato e problema

Reformular a jornada de clientes e fornecedores, o modelo de dados que a sustenta e a importação assistida. O proprietário identificou desalinhamento, ambiguidade entre buscar/cadastrar, ausência de identificação fiscal/endereço/unidades/fornecimentos e necessidade de preparar interoperabilidade com Panne e pagamentos integrados.

A mensagem nativa “Preencha este campo” ao clicar Criar com nome vazio demonstra validação HTML, não falha comprovada de gravação. O defeito de UX é apresentar um formulário mínimo de submissão como se fosse a entrada de uma jornada de cadastro. Reproduzir e registrar o comportamento real.

O analista conferiu a definição inicial de counterparty em V2: identidade/escopo, name, role, active, version e autoria. Isso não é inventário de todas as migrations atuais. Conferir modelo completo, APIs e CatalogsPage antes da mudança. Este trabalho é evolução funcional de cadastro, não apenas CSS. Não inventar capacidades de integração já disponíveis.

## Referência visual proposta

[Lista e formulário propostos](../ux/interface-aprovada/04-cadastros-lista-formulario-proposta.png). Caminho na área do analista: C:\Users\Oscar Sarquis\Documents\Codex\2026-09-25\files-pasted-by-the-user-documento\outputs\interface-aprovada\04-cadastros-lista-formulario-proposta.png.

Esta prancha é proposta nova para revisão, não aceite prévio do proprietário. Usar as duas barras de navegação e identidade já aprovadas. A imagem não especifica comportamento nem esgota os campos. O texto abaixo prevalece: não adicionar busca global fictícia; escolher um só controle para filtrar relação (não duplicar chips e dropdown); relação cliente/fornecedor admite ambos e deve usar seleção compatível, não rádios exclusivos; placeholders não são valores gravados. Copiar a imagem para pasta documental estável ao registrar o prompt.

## Lista e descoberta

Página Clientes e fornecedores com busca por nome, nome fantasia, documento ou referência externa. Busca é somente consulta, separada do formulário de cadastro. Filtros reais: relação (todos/clientes/fornecedores/ambos), situação, identificação pendente e origem quando houver. Paginação e contagens abrangem o conjunto autorizado, não apenas a página carregada.

Botão “Cadastrar” abre página de cadastro mesmo com busca vazia. Não exige um nome prévio na lista. Pode oferecer “Cadastrar fornecedor” conforme contexto do filtro, mas nunca selecionar Ambos como padrão silencioso. Um registro pode ser cliente e fornecedor sem duplicar a pessoa.

Lista com nome/documento, relação, localidade, situação e origem de cadastro. Documento mascarado conforme permissão e necessidade. Nome abre detalhe; referências técnicas completas em área secundária. Empty state diferencia ausência de cadastros de ausência de resultados. Inativos permanecem pesquisáveis, evitando recriação acidental.

## Cadastro e detalhe

Página dedicada, sem painel lateral estreito, com seções alinhadas e navegação de retorno que preserva filtros. Ações Cancelar e Cadastrar fornecedor/cliente; edição usa Salvar alterações. Mensagens junto dos campos e resumo acessível dos erros; preservar conteúdo em falha.

| Seção | Dados e regras |
|---|---|
| Identificação | Pessoa jurídica, física ou não informada; razão social/nome; nome fantasia quando aplicável; tipo, país e número do documento; relação cliente/fornecedor; situação. |
| Unidades | Nome da unidade; tipo loja, depósito, armazém, produtor local, escritório ou outro; principal/opcional; documento próprio quando realmente existente, sem copiar automaticamente o da matriz. |
| Endereço | País, CEP/código postal, logradouro, número ou sem número, complemento, bairro, município, UF/região. Vincular à unidade/uso adequado; suportar endereço incompleto sem inventar dados. |
| Contatos | Nome, função, e-mail e telefone; contato principal; multiplicidade definida no modelo. Não assumir e-mail como identidade única. |
| Fornecimentos | Produtos/serviços fornecidos, categorias de fornecimento e observações. Não confundir com categoria financeira nem criar catálogo de estoque. |
| Origem e histórico | Manual, arquivo ou sistema; ID externo, data de observação/importação, autoria e alterações. |

Nome e relação são necessários para cadastro mínimo; documento, endereço e outros dados podem ficar explicitamente incompletos. Permitir produtor ou pessoa sem CNPJ; não criar número fictício. Requisitos de uma integração específica podem impedir envio/uso naquela integração, sem impedir todo cadastro manual. Mostrar completude por finalidade, não chamar cadastro mínimo de beneficiário apto a pagamento.

Documento é texto normalizado com tipo/país; não usar inteiro nem perder zeros. Conferir formatos vigentes em fontes oficiais antes de implementar validação, inclusive evolução do CNPJ alfanumérico. Validade sintática não prova existência, situação fiscal ou titularidade. Consultas de enriquecimento de documento/CEP só com fonte identificada e capacidade contratada; não adicionar chamadas silenciosas de terceiros.

Detalhe apresenta identidade, unidades, contatos, fornecimentos, vínculos externos e histórico; permite editar/inativar com regras claras. Não excluir fisicamente cadastro referenciado por fatos financeiros. Inativação não apaga títulos nem altera baixas existentes.

## Duplicidades e identidade

Ao informar documento ou nome, apresentar candidatos existentes antes da confirmação. Busca por nome sugere, mas não bloqueia por homonímia nem funde registros automaticamente. Documento normalizado exato é chave forte dentro do escopo de empresa e tipo/país; decidir explicitamente o tratamento de matriz/filiais e unidades antes de criar unique index.

Conferir duplicatas legadas antes de aplicar restrição nova. Não reescrever vínculos de títulos automaticamente. Quando existir cadastro compatível, oferecer abrir/vincular/enriquecer mediante revisão, sem recriar. Tratar duas tentativas concorrentes no servidor e banco, além da checagem visual. Nenhuma busca deve revelar dados de outra empresa.

Identidade externa usa empresa, sistema/conexão e ID na origem, não nome. Documento não autoriza junção entre empresas e não é necessariamente a mesma identidade da unidade fornecedora. Não inventar ID fiscal para registros legados.

## Importação assistida agora

Entregar primeiro importação por arquivo CSV com modelo documentado e prévia. Se XLSX for incluído, especificar tratamento seguro sem executar fórmulas/macros. Não anunciar formatos não suportados. Upload não grava automaticamente.

Fluxo: selecionar arquivo → mapear colunas → validar e mostrar linhas → classificar novos, possíveis duplicados, conflitos e inválidos → usuário confirma operações selecionadas → relatório do que foi gravado/rejeitado. Não sobrescrever campo preenchido com vazio. Conflitos exigem escolha explícita; reapresentar revisão se cadastro mudou desde a prévia.

Modelar lote/linha/resultados e idempotência para retomada e repetição sem duplicar. Identificar se gravação é atômica por lote ou por linha; nunca afirmar sucesso total em processamento parcial. Guardar rastreio suficiente com retenção/minimização adequada, evitando payload pessoal em logs. Fórmulas não devem ser executadas nem propagadas de forma perigosa em relatórios exportados.

Fornecer modelo de arquivo sem dados pessoais reais. Importar dados sintéticos somente no ambiente controlado. Não importar cadastros em produção automaticamente como parte do deploy.

## Preparação de Panne e ActionHub

Levantar em leitura os campos reais do fornecedor no Panne: a captura comprova ao menos nome e campo CNPJ, não uma API disponível. Mapear propriedade dos dados, IDs e contratos necessários. Integrar sistemas sempre por AF → Spider → provider de origem; nenhum acesso direto do Finance ao banco Panne como atalho.

Neste recorte, registrar o vínculo externo e preparar o contrato/mapeamento. Não publicar botão “Importar do Panne” funcional por simulação nem ativar integração ainda inexistente. Importação de arquivo exportado é manual e deve ser rotulada assim, não prova de conector Spider. Expor conector somente após implementação e prova real autorizada.

Cadastro de fornecedor não é autorização de pagamento. Dados bancários/Pix e identificação do beneficiário exigem jornada própria de coleta, confirmação, permissão e auditoria; não acrescentar campos livres e tratá-los como destino aprovado. ActionHub permanece módulo integrado de pagamentos; não presumir payout disponível nem obrigar pagamentos externos a passar pelo Mercado Pago. Associar futuro beneficiário sem confundi-lo com contato, estabelecimento ou contraparte.

## Modelo e migração

Entregar dicionário físico com tipo, nulabilidade, cardinalidades, PK/FK, escopo, índices, normalização e histórico. Reaproveitar counterparty e seus IDs. Entidades candidatas: unidades, endereços, contatos, fornecimentos, identidades externas e lotes/linhas de importação. Ajustar à base real, sem criar abstrações sem uso.

Migrations incrementais preservam títulos e referências existentes. Backfill somente de informação comprovada já existente; campos desconhecidos permanecem nulos/pendentes. Validar grants de runtime, unicidade por escopo, versionamento concorrente e autorização em todas as operações. Não transformar o enum atual em um modelo novo sem compatibilidade/revisão explícita.

## Provas e entrega

Implementar e verificar em ambiente controlado: cadastrar sem preencher busca; fornecedor PJ com unidade/endereço; pessoa sem documento; relação ambos; duplicidade exata/semelhante; concorrência; inativação de registro referenciado; importação repetida/parcial/conflitante; isolamento por empresa e viewer sem escrita; rascunho/cancelamento; falha e retry com idempotência. Testes integrados com Postgres real, além de frontend.

Inspecionar desktop/mobile 360, 768, 1280 e tela ampla: alinhamento, ordem de leitura, labels, campos longos, erros, teclado e ações alcançáveis. Preservar duas barras e ausência de Mais/sidebar. Comparar com a proposta e registrar diferenças; dados de demonstração não são evidência da origem.

Criar ACTIONFINANCE_REV_REFORMULACAO_CADASTROS_011.md com modelo, migrações, matriz fonte/campo, provas, gaps dos conectores e telas. Atualizar documentos de domínio/dados/UX e índice sem reescrever histórico. Copiar este prompt como documento novo.

Preparar pacote de publicação com backup/validação da migração e rollback compatível; não assumir que autorizações anteriores de CSS permitem migration e importação produtiva. O pedido autoriza desenvolver esta reformulação e torná-la revisável. Apresentar pacote concreto antes de aplicar mudanças de dados em produção. Não iniciar pagamentos, convite, envio de mensagens ou integração Panne por inferência.

Aceite do novo desenho e da implementação permanece com analista/proprietário. Pendências dos demais ciclos continuam separadas.
