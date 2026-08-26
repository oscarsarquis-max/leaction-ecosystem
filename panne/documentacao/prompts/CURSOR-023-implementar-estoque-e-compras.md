# CURSOR-023 — Implementar Estoque e Compras

Execute no workspace `leaction-ecosystem` e trabalhe exclusivamente em `panne/`.

## 1. Situação inicial obrigatória

O CURSOR-023 será executado **diretamente sobre o CURSOR-022 ainda não versionado**. Não reverta, descarte, reorganize ou perca o trabalho do 022.

Antes de alterar qualquer arquivo, confirme:

- branch `main` e upstream `origin/main`;
- HEAD Git esperado: `7086faa` (`fix(infra): include panne in LAN db sync`);
- working tree contendo somente o CURSOR-022 em `panne/`, além dos leftovers preexistentes;
- Alembic head de código do working tree: `0019_reporting_analytics`;
- baseline do working tree: backend 239 aprovados e 1 Bedrock vivo ignorado;
- frontend: 75 aprovados, typecheck, lint e build verdes;
- `panne/.tmp-chrome-017/` preservado fora do escopo.

Registre a cadeia explicitamente:

`7086faa → CURSOR-022 local/0019 → CURSOR-023 local/0020`

Se houver alteração incompatível ou arquivo estranho dentro de `panne/`, documente antes de prosseguir. Não faça limpeza destrutiva.

## 2. Restrições absolutas

- Trabalhe somente em `panne/`.
- Não acessar MySQL, FTP, `.env` ou aplicações irmãs.
- Não implementar contabilidade de estoque, custo médio, FIFO/LIFO financeiro ou escrituração.
- Não implementar contas a pagar, fluxo de caixa, fiscal, emissão de nota ou folha.
- Não enviar pedidos a fornecedores ou marketplaces externos.
- Não comprar automaticamente.
- Não alterar fatos históricos de produção, custos ou relatórios.
- Não transformar falta de saldo em saldo zero presumido.
- Não permitir movimentação de estoque por IA.
- Não fazer commit, push ou deploy.
- Não iniciar o CURSOR-024.

## 3. Objetivo

Implementar o domínio operacional de **Estoque e Compras** da Panne, cobrindo:

- locais de estoque;
- itens estocáveis vinculados aos ingredientes existentes;
- lotes, validade e rastreabilidade;
- ledger imutável de movimentações;
- saldo atual e saldo por lote/local;
- reservas para ordens de produção;
- separação e consumo vinculados à produção;
- inventário físico e ajustes auditáveis;
- políticas de saldo negativo, lote e validade;
- ponto de reposição e sugestão determinística de compra;
- requisição de compra;
- cotação registrada manualmente;
- pedido de compra;
- recebimento e entrada por lote;
- devolução ao fornecedor;
- integração com fornecedores, preços, custos, rastreabilidade e relatórios já existentes.

Estoque deve ser um ledger quantitativo e rastreável. Compras devem depender de decisões humanas. Nada deve ser enviado externamente neste ciclo.

## 4. Auditoria e reconciliação

Antes de implementar, audite e documente:

- `ingredient`, versões e unidades;
- `supplier`, `supplier_item` e `supplier_item_price`;
- conversões de unidade existentes;
- formulações e escalas;
- planos, ordens, bateladas e snapshots de materiais;
- pesagem, consumo, retorno, desperdício e correção;
- eventos de produção e rastreabilidade;
- políticas e cálculos de custo;
- relatórios e métricas do CURSOR-022;
- permissões, papéis e RLS.

Produza uma matriz de reconciliação com:

- fato já existente;
- fato novo necessário;
- vínculo;
- granularidade;
- autoridade sobre o dado;
- impacto histórico;
- estratégia para registros anteriores ao 0020.

Não copie ingredientes, fornecedores, ordens, consumos ou preços.

## 5. Vocabulário canônico

Defina claramente:

- **local de estoque:** espaço lógico/físico em um estabelecimento;
- **item estocável:** identidade organizacional que aponta para ingrediente e unidade canônica;
- **lote interno:** unidade rastreável recebida ou produzida;
- **lote do fornecedor:** identificação externa preservada como dado;
- **movimentação:** evento quantitativo append-only;
- **saldo físico:** soma das movimentações efetivas;
- **reservado:** quantidade comprometida, ainda fisicamente disponível;
- **disponível:** saldo físico menos reservas ativas;
- **em trânsito:** pedido emitido e ainda não recebido, sem compor saldo físico;
- **separado:** reservado e associado a ordem/batelada, sem equivaler a consumo;
- **consumo:** fato de produção que reduz estoque quando postado;
- **retorno:** material devolvido pela produção ao estoque;
- **desperdício/descarte:** saída sem retorno ao disponível;
- **inventário:** contagem física em data e local definidos;
- **ajuste:** movimentação explícita que reconcilia diferença; nunca edição de saldo;
- **FEFO:** sugestão operacional pelo vencimento mais próximo; não método contábil de custeio.

Pesagem, separação, consumo e movimentação de estoque são fatos distintos.

## 6. Política de estoque

Criar política versionada por organização e, quando necessário, por estabelecimento:

- saldo negativo: negar por padrão;
- lote obrigatório, opcional ou não aplicável;
- validade obrigatória por categoria;
- consumo de lote: escolha manual ou sugestão FEFO;
- tolerância de recebimento;
- tolerância de inventário;
- reserva na liberação da ordem ou por comando posterior;
- tratamento de ordem cancelada;
- tratamento de retorno e desperdício;
- aprovação exigida para ajustes;
- dias de alerta de validade;
- algoritmo e versão;
- autor, vigência e justificativa.

Política publicada é imutável. Mudança gera nova versão. Operações registram o snapshot da política usada.

## 7. Itens e locais de estoque

Implementar:

- local vinculado a estabelecimento e organização;
- código único, nome, tipo, situação e responsável opcional;
- item estocável vinculado a ingrediente organizacional;
- unidade canônica compatível;
- controle por lote e validade conforme política;
- ponto de reposição, estoque de segurança e quantidade-alvo opcionais;
- fornecedor/item preferencial apenas como preferência explícita;
- ativação e desativação sem exclusão histórica.

Um ingrediente pode ter diferentes itens de fornecedor, mas não deve ganhar identidades duplicadas para cada compra.

## 8. Lotes e validade

Cada lote deve preservar:

- item estocável;
- organização, estabelecimento e local;
- lote interno;
- lote do fornecedor quando informado;
- fornecedor e item de fornecedor;
- fabricação quando informada;
- validade quando aplicável;
- recebimento de origem;
- unidade e quantidade recebida;
- estado `available`, `quarantined`, `blocked`, `expired`, `exhausted` ou `closed`;
- motivo e ator de bloqueio/liberação;
- hashes e referências de rastreabilidade.

Lote vencido, bloqueado ou em quarentena não pode ser sugerido nem consumido sem override humano auditável e permissão específica. O sistema não deve inferir validade ausente.

## 9. Ledger de movimentações

Criar ledger append-only com tipos controlados:

- recebimento;
- transferência de saída;
- transferência de entrada;
- separação/reserva não deve alterar saldo físico;
- consumo de produção;
- retorno de produção;
- desperdício/descarte;
- devolução ao fornecedor;
- ajuste positivo;
- ajuste negativo;
- reversão;
- correção por novo lançamento;
- abertura controlada de saldo inicial.

Cada movimentação deve registrar:

- item, lote, local de origem/destino conforme o tipo;
- quantidade informada e unidade;
- quantidade canônica e conversão;
- sinal e natureza;
- origem do fato;
- ordem, batelada, consumo, recebimento ou inventário quando aplicável;
- ator, data efetiva, data de registro;
- correlação, causação e idempotência;
- política e versão;
- motivo quando exigido;
- hash.

Movimentação nunca é editada ou apagada. Erro é corrigido por reversão ou lançamento compensatório autorizado.

## 10. Saldo e concorrência

Saldo deve ser uma projeção reconciliável do ledger, por:

- organização;
- estabelecimento;
- local;
- item;
- lote;
- unidade canônica.

Implemente proteção concorrente para impedir dupla saída ou reserva acima do disponível quando a política negar saldo negativo.

Requisitos:

- lock transacional adequado;
- idempotência;
- ordenação estável;
- reserva e baixa atômicas;
- nenhum cálculo em `float`;
- teste de duas operações concorrentes;
- projeção reconciliável com o ledger.

Se usar tabela de saldo projetado por desempenho, ela é cache derivado e deve ser reconstruível, transacionalmente consistente e nunca a fonte histórica.

## 11. Reservas e ordens de produção

Implementar reservas por ordem e, opcionalmente, batelada:

- a partir dos snapshots de materiais da ordem;
- por item e quantidade canônica;
- alocação por lote/local separada da necessidade total;
- estados `pending`, `partial`, `reserved`, `released`, `consumed`, `cancelled` e `expired`;
- reserva parcial explícita;
- insuficiência documentada;
- liberação automática da reserva somente por regra determinística em cancelamento ou encerramento;
- preservação do histórico.

Ordens anteriores ao 0020 não recebem reservas retroativas silenciosas. Deve existir comando humano de adoção/reconciliação, com pré-condições, motivo e auditoria.

Reserva não altera saldo físico; altera apenas disponível.

## 12. Separação e integração com produção

Permitir separação digital por ordem/batelada:

- sugestão de lotes por FEFO;
- confirmação humana dos lotes e quantidades;
- lote real congelado na separação;
- divergência e substituição auditáveis;
- etiqueta/lista de separação imprimível;
- sem QR obrigatório neste ciclo.

Integre o consumo da produção ao estoque sem duplicar o ledger de produção:

- o `production_material_consumption` continua fonte operacional;
- um lançamento de estoque referencia o consumo de origem;
- a postagem deve ser idempotente;
- retorno e desperdício geram movimentos distintos;
- consumo sem lote quando lote é obrigatório deve ser bloqueado;
- falha de estoque não pode apagar o fato operacional já persistido; defina transação/estado pendente de postagem de forma segura;
- não reinterpretar consumos históricos automaticamente.

Documente claramente a fronteira transacional entre execução e estoque.

## 13. Inventário físico

Implementar:

- sessão de inventário por local e data de corte;
- escopo congelado de itens/lotes;
- contagens append-only;
- primeira e segunda contagem opcionais;
- divergência calculada;
- revisão humana;
- aprovação com permissão;
- ajuste por movimentos explícitos;
- fechamento imutável;
- reabertura proibida; correção por novo inventário ou movimento autorizado.

Durante o inventário, a política deve definir se o local fica bloqueado ou se movimentos posteriores ao corte são conciliados. Não editar saldo diretamente.

## 14. Reposição determinística

Implementar sugestão, não compra automática:

- saldo físico;
- reservas;
- disponível;
- pedidos em trânsito;
- demanda planejada em horizonte explícito;
- estoque de segurança;
- ponto de reposição;
- quantidade-alvo;
- embalagem do fornecedor;
- múltiplo mínimo quando cadastrado;
- validade e risco de excesso, quando possível.

Toda sugestão deve explicar fórmula, dados utilizados, cobertura e lacunas. Ausência de lead time, embalagem ou demanda deve permanecer explícita.

Não usar IA ou previsão estatística neste ciclo.

## 15. Requisição e cotação

Implementar requisição de compra:

- manual ou derivada de sugestão;
- item, quantidade, unidade, necessidade e data desejada;
- estabelecimento/local de destino;
- justificativa e origem;
- estados `draft`, `submitted`, `approved`, `rejected`, `converted`, `cancelled`;
- aprovação humana e trilha.

Implementar registro de cotações recebidas manualmente:

- fornecedor e item;
- quantidade/embalagem;
- preço e moeda;
- prazo;
- validade da proposta;
- condições textuais controladas;
- evidência/referência;
- comparação determinística por preço unitário compatível e prazo;
- nenhuma escolha automática de fornecedor.

Cotação não substitui o histórico canônico de preços sem confirmação humana.

## 16. Pedido de compra

Implementar pedido interno versionado:

- organização, estabelecimento, fornecedor e destino;
- itens, quantidades, embalagens e preços acordados;
- moeda BRL na v1;
- datas previstas;
- vínculo com requisições/cotações;
- estados `draft`, `approved`, `issued`, `partially_received`, `received`, `cancelled`, `closed`;
- numeração única por organização;
- aprovação e emissão humanas;
- alterações materiais após emissão por revisão ou substituição, nunca reescrita histórica.

`issued` significa registrado como emitido internamente. Não enviar e-mail, EDI, API ou pedido a marketplace.

## 17. Recebimento e devolução

Recebimento deve permitir:

- parcial ou total;
- conferência do pedido;
- quantidade recebida e unidade;
- lote do fornecedor;
- fabricação e validade;
- local de destino;
- divergência de quantidade, preço, embalagem ou validade;
- quarentena/bloqueio;
- criação do lote interno;
- entrada no ledger;
- idempotência;
- ator e evidência.

Preço recebido não deve atualizar silenciosamente `supplier_item_price`. Ofereça comando humano separado para registrar o preço observado, com vínculo ao recebimento.

Devolução deve gerar saída vinculada ao recebimento/lote e preservar motivo. Não implementar crédito financeiro ou contas a pagar.

## 18. Rastreabilidade

Ampliar a rastreabilidade canônica para permitir:

- fornecedor → pedido → recebimento → lote → local;
- lote → reserva/separação → ordem/batelada → consumo;
- ordem/batelada → produto e formulação;
- movimentações, ajustes, inventários e devoluções;
- timeline com correlação/causação;
- hashes e versões.

Não criar uma segunda fonte de rastreabilidade. Estenda a projeção existente.

## 19. Custos e preços

O domínio de estoque não calcula custo contábil.

- recebimento pode registrar preço acordado e observado;
- custos do CURSOR-021 continuam soberanos;
- cálculo de custo pode usar preço confirmado conforme sua política;
- movimento de estoque não recebe valoração retroativa automática;
- ajuste de estoque não altera custos históricos;
- nenhuma implementação de FIFO/LIFO/custo médio financeiro.

## 20. Relatórios

Estenda o catálogo do CURSOR-022 sem duplicar seu motor:

- posição de estoque por item/local/lote;
- disponível versus reservado;
- validade próxima e lotes bloqueados;
- movimentações;
- consumo e desperdício por item;
- cobertura de lote;
- divergências de inventário;
- requisições e pedidos por estado;
- recebimentos parciais;
- necessidades de reposição;
- qualidade dos dados de estoque.

Atualize versão do catálogo/métricas. Preserve ausência, cobertura, drill-down, snapshots, CSV e permissões. Não criar relatório de valor contábil de estoque.

## 21. Persistência

Criar migração reversível:

`0020_inventory_procurement`

Após auditoria, modele entidades equivalentes a:

- política e versão de estoque;
- local de estoque;
- item estocável;
- lote;
- movimentação;
- projeção de saldo, se necessária;
- reserva e alocação por lote;
- separação;
- vínculo de postagem do consumo;
- inventário, escopo, contagem e revisão;
- sugestão de reposição e itens;
- requisição de compra e itens;
- cotação e itens;
- pedido de compra, revisão e itens;
- recebimento e itens;
- devolução;
- comando/idempotência.

Exigências:

- UUID;
- `timestamptz`;
- `numeric`/`Decimal`, nunca `float`;
- FKs compostas por organização;
- códigos e sequências únicas;
- estados e checks fechados;
- append-only para movimentos, contagens, decisões e histórico;
- imutabilidade após emissão/fechamento;
- exclusão física bloqueada;
- índices para saldo, validade, reservas e rastreabilidade;
- RLS `ENABLE` + `FORCE`;
- default deny;
- isolamento A/B;
- runtime sem fallback administrativo.

## 22. Permissões

Criar permissões distintas:

- `inventory.read`;
- `inventory.policy.manage`;
- `inventory.item.manage`;
- `inventory.lot.manage`;
- `inventory.reserve`;
- `inventory.separate`;
- `inventory.move`;
- `inventory.adjust`;
- `inventory.count`;
- `inventory.count.approve`;
- `inventory.expired.override`;
- `procurement.read`;
- `procurement.requisition.create`;
- `procurement.requisition.approve`;
- `procurement.quotation.manage`;
- `procurement.order.manage`;
- `procurement.order.approve`;
- `procurement.receive`;
- `procurement.return`;
- `reporting.inventory.read`.

Padeiro pode consultar/separar/consumir apenas conforme papel e política; não aprova ajuste ou compra. Cognito groups e `legacy_role_label` não autorizam.

## 23. HTTP, idempotência e segurança

Implementar APIs tipadas para políticas, locais, itens, lotes, saldos, reservas, separação, movimentos, inventários, reposição, requisições, cotações, pedidos, recebimentos, devoluções e rastreabilidade.

Exigências:

- sessão runtime;
- RLS soberana;
- `Idempotency-Key` nos comandos;
- `If-Match`/`row_version` em estados mutáveis;
- locks em saldo, reserva, recebimento e inventário;
- allowlist de filtros/ordenação;
- contratos fechados e sem mass assignment;
- erros sanitizados em português;
- token somente em memória no frontend;
- nenhum segredo ou dado sensível em logs;
- nenhuma chamada externa nos testes comuns.

## 24. Interface e arquitetura da informação

Não criar novo item horizontal de primeiro nível.

Usar a estrutura canônica:

### Componentes

- Ingredientes;
- Estoque;
- Lotes e validade;
- Fornecedores;

### Gestão

- Compras;
- Inventários;
- Relatórios e painéis.

Subáreas de Estoque:

- Visão geral;
- Posição;
- Reservas;
- Movimentações;
- Validades;
- Separação.

Subáreas de Compras:

- Necessidades;
- Requisições;
- Cotações;
- Pedidos;
- Recebimentos;
- Devoluções.

Preservar Oficina + Atelier, menus horizontais com submenus, área útil ampla, paleta bege/grafite, logos autorizados, desktop/notebook/tablet e ausência de barra lateral permanente.

## 25. Interface operacional

Implementar:

- cartões de saldo físico, reservado, disponível e em trânsito;
- tabela densa por item/local/lote;
- badges de validade, bloqueio, cobertura e divergência;
- fluxo guiado de reserva/separação;
- recebimento orientado por pedido;
- inventário com primeira/segunda contagem;
- comparação de cotações sem escolher fornecedor automaticamente;
- pedido com histórico;
- drill-down até movimentos e fatos de origem;
- impressão de lista de separação, pedido interno e conferência de recebimento;
- estados vazio, carregando, parcial, conflito, bloqueio, erro e acesso negado.

Não exibir custo ou preço a perfil sem permissão.

## 26. Assistentes, badges e gamificação

Criar assistentes determinísticos para:

### Reposição e compra

1. verificar necessidade;
2. revisar cobertura e lacunas;
3. confirmar quantidade e embalagem;
4. criar requisição;
5. registrar cotações;
6. comparar;
7. obter aprovação;
8. emitir pedido interno;
9. receber;
10. atualizar preço observado com confirmação opcional.

### Inventário

1. escolher local e corte;
2. congelar escopo;
3. contar;
4. revisar divergências;
5. segunda contagem quando exigida;
6. aprovar;
7. gerar ajustes;
8. fechar.

Permitir minimizar, dispensar e retomar.

Badges e gamificação somente para completude, validade revisada, rastreabilidade e qualidade coletiva. Proibidos ranking individual, pressão por menor compra, ocultação de perdas, contagens ajustadas para “bater” ou compra automática.

IA não é necessária. Se futuramente usada para explicação, nunca poderá movimentar, ajustar, aprovar ou comprar.

## 27. Acessibilidade e dispositivos

- contraste AA;
- teclado e foco visível;
- alvos de toque;
- estados além da cor;
- tabelas responsivas sem esconder dado crítico;
- scanners não são obrigatórios;
- tablet utilizável no recebimento, separação e inventário;
- `prefers-reduced-motion`;
- impressão sem chrome;
- axe sem violações críticas.

## 28. Fora do escopo

- custo médio, FIFO/LIFO financeiro e contabilidade;
- escrituração e fiscal;
- contas a pagar;
- pagamento ou conciliação bancária;
- nota fiscal eletrônica;
- integração automática com fornecedor, Amazon ou marketplace;
- previsão de demanda por IA;
- compra automática;
- código de barras/QR obrigatório;
- balança integrada;
- sensores/IoT;
- armazém avançado/WMS;
- roteirização logística;
- venda e faturamento;
- múltiplas moedas e câmbio;
- offline/PWA.

## 29. Testes obrigatórios

Backend em Python 3.12:

- preservação integral do CURSOR-022;
- migração `0019 ↔ 0020`, reaplicação e `0001 → head`;
- RLS, isolamento A/B e runtime;
- permissões;
- política versionada;
- locais e itens;
- lotes, validade, quarentena e bloqueio;
- ledger append-only;
- saldo reconciliável;
- unidade e conversão;
- concorrência de saída e reserva;
- saldo negativo negado por padrão;
- reserva parcial, liberação e cancelamento;
- ordens anteriores ao 0020;
- separação e FEFO como sugestão;
- postagem idempotente de consumo, retorno e desperdício;
- inventário, dupla contagem e ajuste;
- reposição e ausência de dados;
- requisição e aprovação;
- cotação e comparação;
- pedido, revisão e emissão humana;
- recebimento parcial/total;
- lote criado no recebimento;
- preço observado sem atualização automática;
- devolução;
- rastreabilidade ponta a ponta;
- relatórios de estoque com cobertura e drill-down;
- nenhuma compra automática;
- regressão integral dos 239 testes anteriores.

Frontend:

- typecheck, lint, testes e build;
- menus Componentes/Gestão;
- saldos e lotes;
- reserva e separação;
- validade/bloqueio;
- inventário;
- necessidades e requisições;
- cotações;
- pedidos;
- recebimento e devolução;
- permissões e troca de organização;
- 409 e recarregamento;
- assistentes;
- acessibilidade e responsividade;
- ausência de custos para perfil não autorizado.

Nenhuma chamada externa nos testes comuns.

## 30. Evidências e documentação

Produzir evidências em:

`panne/documentacao/evidencias/cursor-023/`

Incluir:

- visão de estoque;
- saldo por lote/local;
- validade e bloqueio;
- reserva;
- separação;
- movimento e rastreabilidade;
- inventário e divergência;
- necessidade de reposição;
- requisição;
- comparação de cotações;
- pedido;
- recebimento parcial;
- devolução;
- relatórios de estoque;
- desktop, notebook, tablet horizontal e vertical.

Documentar:

- ADR;
- reconciliação;
- vocabulário;
- política de estoque;
- modelo de dados;
- ledger e saldos;
- lotes e validade;
- reservas e produção;
- inventário;
- reposição;
- compras e recebimentos;
- rastreabilidade;
- fronteira com custos;
- extensão dos relatórios;
- permissões e RLS;
- concorrência/idempotência;
- acessibilidade;
- limitações;
- prompt e retorno;
- atualização do `INDICE.md`.

## 31. Retorno obrigatório

Informe numeradamente:

1. base, branch, HEAD e cadeia local 022→023;
2. isolamento;
3. preservação do CURSOR-022;
4. auditoria e reconciliação;
5. banco e Alembic head;
6. tabelas;
7. política de estoque;
8. locais e itens;
9. lotes e validade;
10. ledger;
11. saldo e concorrência;
12. reservas;
13. separação;
14. integração com consumo, retorno e desperdício;
15. tratamento de ordens anteriores;
16. inventário físico;
17. reposição;
18. requisições;
19. cotações;
20. pedidos;
21. recebimentos;
22. devoluções;
23. fornecedores e preços observados;
24. rastreabilidade;
25. fronteira com custos;
26. relatórios;
27. permissões;
28. RLS e segurança;
29. HTTP, idempotência e concorrência;
30. interface;
31. assistentes, badges e gamificação;
32. acessibilidade e responsividade;
33. migrações;
34. testes backend;
35. testes frontend;
36. documentação e evidências;
37. riscos e limitações;
38. segredos e estado do Git;
39. confirmação de ausência de commit, push e deploy;
40. confirmação explícita de que o CURSOR-024 não foi iniciado.

Pare ao concluir.

</user_query>
