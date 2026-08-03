# QMind — Arquitetura Inicial do Sistema

## Status

Documento de direção inicial. As tecnologias específicas ainda não estão decididas.

## Visão arquitetural

O QMind deverá iniciar como uma aplicação modular, com fronteiras claras de domínio e possibilidade de separar componentes quando escala ou autonomia operacional justificarem. O objetivo é evitar tanto um monólito desorganizado quanto uma distribuição prematura em muitos serviços.

## Contextos de domínio propostos

- Identidade e acesso: usuários, papéis, permissões e autenticação.
- Organizações: clientes, unidades, equipes e segregação de dados.
- Referenciais: normas, versões, requisitos e critérios de avaliação.
- Processos: processos organizacionais, responsáveis e interações.
- Avaliações: planejamento, escopo, entrevistas e respostas.
- Evidências: documentos, registros, observações e vínculos.
- Constatações: conformidades, lacunas, riscos e oportunidades.
- Maturidade: modelos, dimensões, pontuações e justificativas.
- Ações: planos, responsáveis, prazos, validação e eficácia.
- Relatórios: modelos, revisões, aprovação e publicação.
- Assistência de IA: recuperação de contexto, geração, revisão e auditoria.

## Camadas lógicas

1. Experiência: interfaces web e móvel.
2. Aplicação: casos de uso, orquestração e autorização.
3. Domínio: regras, entidades, políticas e eventos.
4. Infraestrutura: persistência, arquivos, integrações e provedores de IA.

As regras de negócio não deverão depender diretamente de frameworks, banco de dados ou provedor de IA.

## Fluxo de rastreabilidade

```text
Referencial -> Requisito -> Pergunta/critério -> Evidência
            -> Análise -> Constatação -> Ação -> Verificação de eficácia
```

Relatórios e indicadores deverão ser derivados desse encadeamento, preservando autoria, data e versão.

## Multiempresa e segurança

- Todo dado de negócio deverá pertencer explicitamente a uma organização.
- A autorização deverá combinar organização, papel e escopo do recurso.
- Arquivos e índices de busca deverão respeitar a mesma segregação.
- Operações sensíveis deverão produzir trilha de auditoria.
- Segredos e credenciais não deverão ser armazenados no código.

## Integração de IA

A IA deverá ser acessada por uma camada própria, independente do fornecedor. Essa camada será responsável por:

- seleção e montagem do contexto autorizado;
- registro de modelo, prompt e parâmetros;
- validação de saída estruturada;
- referências às fontes utilizadas;
- políticas de privacidade e retenção;
- revisão humana e registro de aceitação ou alteração;
- avaliação de qualidade, custo e latência.

## Dados e arquivos

- Dados transacionais: banco relacional.
- Evidências e relatórios: armazenamento de objetos com metadados.
- Busca semântica: índice opcional e segregado, introduzido quando necessário.
- Auditoria: registros imutáveis ou protegidos contra alteração indevida.
- Exportação: formatos abertos sempre que possível.

## Qualidades prioritárias

- Segurança e privacidade.
- Rastreabilidade e auditabilidade.
- Clareza das regras de negócio.
- Disponibilidade adequada ao uso profissional.
- Usabilidade em desktop e campo.
- Testabilidade e facilidade de evolução.
- Observabilidade de falhas, custos e desempenho.

## Decisões pendentes

- Plataforma e linguagem do backend.
- Estratégia web, móvel e funcionamento offline.
- Banco de dados e armazenamento de objetos.
- Provedor ou provedores de identidade.
- Provedores e modelos de IA.
- Estratégia de hospedagem, regiões e recuperação.
- Política detalhada de retenção e descarte de dados.

Cada decisão relevante deverá receber um ADR antes da implementação correspondente.

