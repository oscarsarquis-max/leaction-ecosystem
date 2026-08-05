# ADR-008 — Camada e governança de inteligência artificial

- Status: Aceito
- Aceito em: 2026-08-03
- Base de aceite: `../04_Docs/005_Monorepo_Confrontation.md`
- Data: 2026-08-03
- Responsáveis: equipe QMind

## Contexto

A IA poderá apoiar entrevistas, sínteses, classificação preliminar, recuperação de referências e elaboração de rascunhos. Como o QMind trata evidências e conclusões técnicas, respostas plausíveis porém incorretas, vazamento entre organizações, injeção de prompt ou automação excessiva podem causar dano relevante.

## Decisão proposta

Implementar a IA por uma **camada própria e independente de fornecedor**, subordinada aos casos de uso do QMind. O modelo não terá acesso direto ao banco, armazenamento, credenciais ou ferramentas privilegiadas.

Toda saída técnica será tratada como sugestão até revisão humana. A IA não poderá aprovar constatações, declarar conformidade, publicar relatórios, encerrar ações ou alterar evidências autonomamente.

## Fluxo controlado

1. O caso de uso autentica e autoriza usuário, organização e finalidade.
2. O QMind recupera somente fontes permitidas e versionadas.
3. Conteúdo não confiável é delimitado como dado, nunca como instrução.
4. A camada monta prompt, parâmetros e formato de saída.
5. O provedor gera uma resposta sem executar ações externas.
6. A saída é validada estruturalmente e submetida a verificações aplicáveis.
7. O usuário revisa, edita, aceita ou rejeita a sugestão.
8. O sistema registra proveniência e decisão humana.

## Proveniência mínima

- caso de uso e organização;
- usuário solicitante;
- provedor, modelo e versão ou identificador disponível;
- versão do prompt e parâmetros relevantes;
- identificadores das fontes recuperadas;
- data, latência, consumo e resultado;
- validações executadas;
- aceitação, edição ou rejeição pelo usuário.

Logs evitarão armazenar conteúdo sensível integral quando métricas e referências forem suficientes.

## Requisitos das respostas

- Distinguir requisito, evidência, inferência e recomendação.
- Citar fontes internas específicas quando a tarefa depender delas.
- Declarar insuficiência de evidência em vez de preencher lacunas.
- Usar saída estruturada e validável quando alimentar a aplicação.
- Não reproduzir instruções ocultas, credenciais ou dados de outra organização.
- Mostrar ao usuário que o conteúdo é assistido por IA e aguarda revisão quando aplicável.

## Segurança

- Prompts de usuário, documentos e páginas recuperadas serão considerados não confiáveis.
- Instruções encontradas dentro de evidências não poderão modificar políticas do sistema.
- Ferramentas futuras usarão permissões mínimas, argumentos validados, limites e confirmação humana para efeitos relevantes.
- Saídas nunca serão executadas como código, consulta ou comando sem validação determinística e autorização específica.
- Limites de custo, tamanho, frequência e tempo serão aplicados por caso de uso.
- Filtros de organização serão impostos antes da busca textual ou vetorial.

## Privacidade e dados

- O fornecedor não poderá usar dados do QMind para treinamento sem autorização contratual explícita.
- Retenção, região, subprocessadores e descarte deverão ser avaliados antes da contratação.
- Dados pessoais e confidenciais serão minimizados ou mascarados quando possível.
- Ambientes não produtivos não receberão dados reais sem processo autorizado.
- Embeddings e outros derivados herdarão organização, classificação e retenção das fontes.

## Avaliação e mudanças

Cada caso de uso terá um conjunto versionado de testes contendo exemplos normais, insuficiência de evidência, tentativa de injeção, conflito de fontes e conteúdo sensível.

Métricas mínimas:

- correção e aderência às fontes;
- taxa de alegações sem suporte;
- aceitação, edição e rejeição humana;
- vazamento ou mistura de contexto;
- robustez a injeção de prompt;
- latência, disponibilidade e custo.

Mudança de modelo, prompt, estratégia de recuperação ou ferramenta crítica exigirá avaliação antes da promoção. Deverá existir mecanismo de desativação por funcionalidade.

## Alternativas consideradas

### Chamadas diretas ao fornecedor em cada módulo

Rejeitadas porque dispersariam políticas, auditoria, custos e tratamento de falhas.

### Um único modelo para todas as tarefas

Não adotado como regra. Modelos serão selecionados por risco, qualidade, privacidade, custo e latência.

### Agente autônomo com acesso amplo

Rejeitado para a fase inicial devido ao risco de ações indevidas, vazamento e baixa previsibilidade.

### Treinamento ou fine-tuning imediato

Não adotado antes de existir necessidade comprovada, base lícita, conjunto de avaliação e governança de dados.

## Consequências

### Positivas

- Troca de fornecedor e comparação de modelos facilitadas.
- Políticas de segurança e auditoria centralizadas.
- Revisão humana e proveniência verificáveis.
- Evolução orientada por avaliação, não apenas por demonstrações.

### Negativas e riscos

- Camada adicional de engenharia e observabilidade.
- Avaliações precisam de manutenção contínua.
- Nenhuma mitigação elimina completamente respostas incorretas ou injeção de prompt.

## Critérios para escolher fornecedores e modelos

- desempenho comprovado no conjunto de avaliação do QMind;
- privacidade, retenção, região e termos de uso de dados;
- segurança, disponibilidade e resposta a incidentes;
- capacidade de saída estruturada e rastreabilidade operacional;
- custo total, limites, latência e portabilidade;
- suporte aos idiomas e documentos dos usuários.

## Critérios para aceitação

- Definir os primeiros casos de uso permitidos e proibidos.
- Criar conjunto inicial de avaliação antes da integração produtiva.
- Demonstrar isolamento entre duas organizações.
- Testar injeção em prompt e em documento recuperado.
- Validar revisão humana e trilha de proveniência.
- Aprovar avaliação de privacidade do fornecedor.

## Confronto com o monorepo (aceite)

- Bedrock (Claude) é o padrão operacional mais próximo (inove); phanton mostra abstração multi-provedor.
- QMind **exige** camada própria: módulos de domínio/API não chamam Bedrock diretamente.
- Provedor inicial elegível: **AWS Bedrock** (região de inferência tipicamente `us-east-1`, independentemente da app em `us-east-2`).
- Casos de uso permitidos/proibidos e suite de avaliação serão definidos antes de qualquer integração produtiva.

## Emenda — economia de tokens de modelo (2026-08-04)

Alinhado a `ADR-010`. Para **tokens de IA** (não JWT/OIDC):

- persistir conhecimento em PostgreSQL, S3 e arquivos versionados;
- prompts curtos; recuperar só trechos necessários; não reenviar conversas inteiras;
- resumos estruturados persistidos; cache de resultados seguros;
- modelos menores para classificação/extração; modelo caro só quando necessário;
- limites de tokens por caso de uso; métricas de custo por organização e operação.

Autenticação continua Cognito (JWT/OIDC) — ver ADR-006 / ADR-010.

## Referências

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST AI 600-1, Generative AI Profile: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- OWASP GenAI Security Project: https://genai.owasp.org/llm-top-10/
- `ADR-002-isolamento-multiempresa.md`
- `ADR-007-armazenamento-de-evidencias.md`

