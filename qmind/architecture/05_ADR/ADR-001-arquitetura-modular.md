# ADR-001 — Arquitetura modular da aplicação

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind precisa sustentar um fluxo integrado de consultoria e auditoria, começando pela ISO 9001:2015 e permitindo incorporar outros referenciais no futuro. O domínio contém áreas relacionadas, mas distintas: organizações, referenciais, processos, avaliações, evidências, constatações, maturidade, ações, relatórios e assistência de IA.

Na fase inicial, a equipe precisa aprender rapidamente com projetos-piloto. A divisão prematura em muitos serviços aumentaria o custo operacional, dificultaria mudanças transversais e criaria contratos distribuídos antes de as fronteiras do domínio estarem validadas. Por outro lado, uma aplicação sem limites internos claros favoreceria acoplamento e dificultaria a evolução.

## Decisão proposta

Construir inicialmente o QMind como um **monólito modular**, organizado por capacidades de negócio e com limites explícitos entre módulos.

Cada módulo deverá:

- possuir responsabilidades e vocabulário bem definidos;
- expor operações por uma interface de aplicação explícita;
- manter suas regras de domínio independentes de interface, banco e fornecedores externos;
- evitar acesso direto às estruturas internas de outro módulo;
- emitir eventos internos quando houver benefício real de desacoplamento;
- possuir testes proporcionais à criticidade de suas regras.

Os módulos iniciais serão:

1. Identidade e acesso;
2. Organizações;
3. Referenciais;
4. Processos;
5. Avaliações;
6. Evidências;
7. Constatações;
8. Maturidade;
9. Planos de ação;
10. Relatórios;
11. Assistência de IA;
12. Auditoria da plataforma.

A implantação poderá começar como uma única unidade executável. Processamentos demorados, como geração de relatórios, extração de documentos e tarefas de IA, poderão usar trabalhadores assíncronos sem transformar cada módulo em um serviço independente.

## Regras de dependência

- A interface chama casos de uso da camada de aplicação.
- A camada de aplicação coordena domínio e portas de infraestrutura.
- O domínio não depende de frameworks, banco de dados, interface ou provedor de IA.
- Integrações externas são acessadas por adaptadores substituíveis.
- Dependências entre módulos devem ser visíveis e testáveis.
- Recursos compartilhados devem ser mínimos; não será criado um módulo genérico de utilidades de negócio.

## Critérios para futura extração de um serviço

Um módulo só deverá ser separado quando houver evidência de pelo menos uma destas necessidades:

- escala ou perfil de carga substancialmente diferente;
- requisito próprio de disponibilidade ou segurança;
- ciclo de entrega realmente independente;
- isolamento de falhas com benefício mensurável;
- integração externa que exija fronteira operacional específica.

A extração exigirá um novo ADR.

## Alternativas consideradas

### Microsserviços desde o início

Não recomendado nesta fase devido ao custo de infraestrutura, observabilidade, contratos distribuídos, testes e consistência de dados antes da validação do produto.

### Monólito organizado apenas por camadas técnicas

Não recomendado porque tende a espalhar uma mesma capacidade de negócio por muitas pastas e facilita dependências cruzadas sem fronteiras claras.

### Plataforma de baixo código como núcleo definitivo

Não adotada como decisão arquitetural geral. Pode ser avaliada para protótipos ou funções periféricas, desde que segurança, rastreabilidade, portabilidade e regras do domínio sejam preservadas.

## Consequências

### Positivas

- Menor complexidade operacional inicial.
- Transações e depuração mais simples.
- Evolução rápida durante a descoberta.
- Fronteiras preparadas para extrações futuras justificadas.
- Regras do domínio protegidas de escolhas tecnológicas.

### Negativas e riscos

- A disciplina dos limites modulares dependerá de validação automatizada e revisão.
- Uma implantação única pode limitar escalabilidade seletiva no futuro.
- Módulos mal definidos podem se transformar em dependências circulares.

## Confronto com o monorepo (aceite)

Confirmado: o monorepo mistura estilos (Flask, FastAPI, Express). O QMind **não** adotará a decomposição multi-processo do Hub. Mantém-se monólito modular implantável como API + trabalhador assíncrono do mesmo código-base. Diagrama de dependências e fluxo completo de diagnóstico serão validados na modelagem de domínio e no primeiro protótipo.

## Referências internas

- `../00_Architecture/000_Project_Vision.md`
- `../00_Architecture/001_System_Architecture.md`
- `ADR-002-isolamento-multiempresa.md`

