# ADR-004 — Experiência web e móvel

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

O QMind será usado tanto em preparação e consolidação de trabalhos quanto durante entrevistas, visitas e auditorias. O primeiro cenário favorece telas amplas; o segundo exige interação rápida, possível uso em tablet ou telefone e tolerância a conectividade instável.

Construir aplicações nativas completas desde o início aumentaria custo e duplicaria decisões antes da validação das jornadas. Ignorar o uso em campo, porém, comprometeria o fluxo principal.

## Decisão proposta

Adotar uma **aplicação web responsiva como experiência inicial**, projetada desde o começo para desktop e tablet, com suporte progressivo aos principais fluxos em telefone.

Capacidades de instalação e operação offline serão introduzidas de forma incremental, começando por rascunhos e filas locais nos fluxos de entrevista e evidências. Uma aplicação nativa só será considerada mediante evidência de necessidade funcional, distribuição, integração com dispositivo ou desempenho.

## Princípios de experiência

- O fluxo deve refletir a linguagem de consultoria e auditoria, não a estrutura técnica.
- O sistema deve deixar claro o que está salvo, pendente, sincronizando ou com conflito.
- Nenhuma sugestão de IA será apresentada como constatação aprovada.
- Evidência, análise, requisito e conclusão devem permanecer visualmente relacionados.
- Ações frequentes em campo devem exigir poucos passos e funcionar com teclado ou toque.
- Acessibilidade será requisito de produto, não correção posterior.

## Jornadas prioritárias

### Desktop e tablet

- configurar organização, processos e avaliação;
- preparar roteiro e escopo;
- conduzir entrevista e registrar respostas;
- revisar evidências e constatações;
- avaliar maturidade;
- elaborar plano de ação e relatório.

### Telefone

- consultar agenda e roteiro;
- registrar nota, observação, foto ou arquivo autorizado;
- consultar itens pendentes;
- acompanhar e atualizar ações simples.

Edição extensa de relatório não será otimizada para telefone no produto mínimo viável.

## Estado e sincronização

- O servidor continuará sendo a fonte oficial dos registros sincronizados.
- Rascunhos locais terão identificação, data e organização explícitas.
- A interface indicará quando o dispositivo estiver offline.
- Operações pendentes serão idempotentes quando enviadas.
- Conflitos não serão resolvidos silenciosamente quando puderem alterar conteúdo técnico.
- Dados locais sensíveis serão minimizados, protegidos e removidos conforme política definida.

O escopo offline detalhado exigirá refinamento de ameaça, privacidade e experiência antes da implementação.

## Design system

- Reutilizar o design system do ecossistema somente após confirmar compatibilidade e manutenção ativa.
- Componentes compartilhados não deverão carregar regras específicas de outra aplicação.
- Estados de carregamento, vazio, erro, permissão negada, offline e conflito serão padronizados.
- Cores não serão o único meio de representar conformidade, risco ou maturidade.
- Componentes críticos deverão funcionar com teclado, foco visível e tecnologias assistivas.

## Segurança e privacidade no cliente

- A interface não será considerada fronteira de autorização.
- Tokens e sessões seguirão a decisão de identidade futura.
- Conteúdo confidencial não deverá permanecer em cache além do necessário.
- Pré-visualização e download de evidências respeitarão permissão e expiração.
- Telemetria evitará capturar evidências, respostas, dados pessoais ou prompts completos.

## Alternativas consideradas

### Aplicações web e nativa simultâneas

Não adotadas inicialmente pelo custo e pela duplicação antes de validar o fluxo principal.

### Aplicação exclusiva para desktop

Rejeitada porque entrevistas e coleta de evidências acontecem frequentemente em campo.

### Aplicação exclusiva para telefone

Rejeitada porque preparação, análise e relatórios exigem grande densidade de informação.

## Consequências

### Positivas

- Um produto inicial acessível em diferentes dispositivos.
- Menor duplicação de equipe, componentes e regras.
- Validação antecipada da experiência em campo.
- Caminho incremental para instalação e offline.

### Negativas e riscos

- Recursos profundos do dispositivo podem ser limitados.
- Offline e sincronização continuam sendo problemas complexos mesmo na web.
- Interfaces densas exigirão adaptação cuidadosa por tamanho de tela.

## Critérios para escolher framework

- compatibilidade com o monorepo e design system existente;
- acessibilidade e suporte a testes automatizados;
- estratégia sustentável de estado, formulários e cache;
- suporte a responsividade, instalação e capacidades offline;
- manutenção, segurança e ciclo de suporte;
- desempenho em equipamentos intermediários.

## Critérios para considerar aplicação nativa

- necessidade recorrente de captura ou processamento indisponível na web;
- offline amplo e prolongado que a solução web não atenda com segurança;
- requisitos de distribuição ou gestão corporativa de dispositivos;
- desempenho comprovadamente insuficiente após medição;
- adoção em campo que justifique o custo adicional.

## Confronto com o monorepo (aceite)

Decisões fechadas após inventário:

- **Stack UI:** Vite + React + TypeScript + Tailwind (padrão próximo a inove4us/phanton; **não** Next.js do Hub).
- **Design system:** tokens e componentes próprios do QMind. Não importar pacotes UI de outras apps sem extrair biblioteca compartilhada com governança explícita.
- Offline, dispositivos-piloto e nível WCAG formal serão refinados na descoberta de jornadas (épico 1 do backlog); princípios deste ADR permanecem vigentes.

## Referências internas

- `ADR-001-arquitetura-modular.md`
- `ADR-003-backend-e-contrato-api.md`

