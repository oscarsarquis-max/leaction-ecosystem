# ADR-002 — Isolamento multiempresa

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind será uma plataforma SaaS que armazenará avaliações, evidências, constatações, planos de ação e relatórios de diferentes organizações. Parte desses dados pode ser confidencial, pessoal ou estratégica. Uma falha que exponha dados entre clientes teria impacto grave sobre confiança, privacidade e continuidade do produto.

O isolamento precisa abranger dados transacionais, arquivos, buscas, tarefas assíncronas, contexto enviado à IA, logs, exportações e rotinas administrativas.

## Terminologia

- Tenant: fronteira de isolamento de um cliente na plataforma.
- Organização: entidade cliente principal; inicialmente corresponde ao tenant.
- Unidade: subdivisão de uma organização, sem criar uma nova fronteira de isolamento por padrão.
- Associação: vínculo de um usuário com uma organização e seus papéis.

## Decisão proposta

Adotar **banco relacional compartilhado com isolamento lógico obrigatório por organização** na fase inicial, sujeito à confirmação da stack e dos mecanismos de segurança disponíveis.

Todo registro de negócio pertencente a cliente deverá conter um identificador de organização não nulo. O contexto da organização será determinado a partir da identidade autenticada e de sua associação ativa; não deverá ser aceito livremente do corpo de uma requisição.

## Controles obrigatórios

### Aplicação e autorização

- Toda operação deverá executar em um contexto explícito de organização.
- Acesso será autorizado por organização, papel, ação e, quando necessário, escopo do recurso.
- Identificadores previsíveis não poderão permitir acesso cruzado.
- Serviços internos e tarefas assíncronas deverão transportar contexto assinado ou reconstruí-lo de fonte confiável.

### Banco de dados

- Tabelas de negócio terão `organization_id` obrigatório e chaves/índices adequados.
- Restrições únicas deverão incluir a organização quando a unicidade for local ao cliente.
- Consultas sem escopo de organização deverão ser proibidas nas rotas normais da aplicação.
- Se o banco escolhido oferecer políticas de segurança por linha adequadas, elas deverão ser avaliadas como defesa adicional, nunca como substituição da autorização da aplicação.
- Migrações e rotinas administrativas terão revisão específica para risco multiempresa.

### Arquivos e evidências

- Chaves de objetos e metadados deverão incluir a organização.
- Downloads usarão autorização no momento do acesso e URLs temporárias quando aplicável.
- Antivírus, classificação, retenção e descarte serão definidos em ADR próprio de armazenamento.

### Busca e inteligência artificial

- Índices textuais ou vetoriais deverão armazenar e exigir filtro de organização.
- A recuperação de contexto ocorrerá antes da chamada ao modelo e apenas com fontes autorizadas.
- Dados de uma organização não serão usados em prompts, avaliações ou ajustes para outra.
- Logs de IA evitarão conteúdo sensível desnecessário e seguirão política de retenção.

### Auditoria e operação

- Ações sensíveis registrarão usuário, organização, operação, recurso, data e resultado.
- Funções de suporte com acesso excepcional deverão ser limitadas, justificadas e auditadas.
- Exportação e exclusão deverão operar por fronteiras explícitas de organização.
- Testes automatizados tentarão acessar recursos entre duas organizações distintas.

## Alternativas consideradas

### Banco separado por organização

Oferece isolamento forte, mas aumenta provisionamento, migrações, monitoramento e custo operacional. Poderá ser introduzido para clientes com requisitos contratuais específicos, mediante novo ADR.

### Schema separado por organização

Melhora parte do isolamento, porém aumenta a complexidade de migrações e conexões conforme o número de clientes cresce. Não é a proposta inicial.

### Banco compartilhado sem coluna obrigatória de organização

Rejeitado por depender excessivamente de convenções e permitir registros sem proprietário definido.

## Consequências

### Positivas

- Operação inicial mais simples e econômica.
- Modelo uniforme para consultas, migrações e observabilidade.
- Possibilidade de aplicar controles em aplicação, banco, arquivos e IA.

### Negativas e riscos

- Uma consulta incorreta pode causar exposição cruzada se as defesas falharem.
- Todos os caminhos de acesso precisam manter corretamente o contexto.
- Trabalhos administrativos e análises globais exigem tratamento privilegiado.

## Critérios de aceitação

Antes de liberar o produto para dados reais:

- testes automatizados de isolamento devem cobrir operações de leitura, escrita, busca, arquivos, filas e IA;
- nenhuma tabela de negócio poderá possuir registro órfão de organização;
- logs e auditoria deverão permitir investigar tentativas de acesso negadas;
- exportação e remoção por organização deverão ser testadas;
- a revisão de segurança deverá confirmar que o identificador de organização não é confiado ao cliente.

## Confronto com o monorepo (aceite)

- O monorepo usa predominantemente `id_clie` (inteiro). O QMind **não** reutilizará esse modelo: o tenant é `organization_id` (UUID) com associações usuário↔organização.
- PostgreSQL oferece RLS; será avaliada como defesa adicional após o esquema estabilizar (ADR-005).
- Banco ou região dedicados por cliente permanecem exceção contratual (novo ADR).
- Inventário de dados pessoais e retenção será detalhado com o modelo de domínio e ADR-007.

## Referências internas

- `../00_Architecture/000_Project_Vision.md`
- `../00_Architecture/001_System_Architecture.md`
- `ADR-001-arquitetura-modular.md`

