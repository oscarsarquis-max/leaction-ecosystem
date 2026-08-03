# QMind — Padrões de Documentação

## Objetivo

Garantir que documentos do projeto sejam claros, rastreáveis e fáceis de manter.

## Regras gerais

- Escrever em português claro; termos técnicos podem manter a forma original quando útil.
- Declarar hipóteses e separar fatos, decisões e propostas.
- Usar datas no formato `AAAA-MM-DD`.
- Incluir links relativos para documentos internos.
- Evitar duplicação; apontar para a fonte oficial do projeto.
- Registrar decisões arquiteturais em ADR, não apenas em atas ou conversas.
- Não reproduzir conteúdo protegido de normas sem licença apropriada.

## Estado dos documentos

Quando relevante, usar um destes estados:

- Rascunho: em elaboração e sujeito a mudanças amplas.
- Em revisão: pronto para avaliação dos responsáveis.
- Aprovado: fonte vigente para o assunto.
- Substituído: preservado como histórico e ligado ao sucessor.

## Revisão mínima

Antes de aprovar um documento, verificar:

- finalidade e público claros;
- consistência com a visão do produto;
- decisões, responsáveis e pendências identificados;
- ausência de dados sensíveis desnecessários;
- links e referências válidos;
- linguagem objetiva e sem ambiguidade crítica.

### Aceite de máquinas de estado

Para documentos de transição de estado, o aceite **não** basta por “cobertura completa”. Confirmar por evento: autor autorizado, pré-condições, efeitos, auditoria, cancelamento e reabertura (ou impossibilidade justificada). Ver `../04_Docs/006_Domain_Acceptance_Checklist.md`.

