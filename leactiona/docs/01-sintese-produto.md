# Síntese do produto — LEACTIONA.COM.BR

Fonte: fase Phanton `sintese_produto` · pipeline `leactiona-lms-migration`  
Referência histórica citada: Projeto LearnFast (context7).

## Resumo

Síntese para a migração do LMS leactiona.com.br baseada no padrão histórico do Projeto LearnFast (context7). A solução foca na substituição de uma instância pesada do Moodle por uma plataforma single-tenant leve, de alta performance e baixo custo na AWS, utilizando rastreamento xAPI via LRS externo (Learning Locker) e garantindo conformidade com a LGPD.

## Pontos-chave

- Substituição do Moodle por arquitetura single-tenant leve e focada em performance.
- Desacoplamento do banco de dados através da integração com LRS externo (Learning Locker).
- Infraestrutura AWS de baixo custo utilizando ECS Fargate, RDS PostgreSQL e CloudFront.
- Conformidade com a LGPD através de criptografia em repouso e controle de privacidade.

## Requisitos para implementação

- Adoção do padrão arquitetural single-tenant herdado do Projeto LearnFast (context7).
- Integração obrigatória com Learning Locker para armazenamento de logs xAPI.
- Configuração de cache agressivo no CloudFront para otimização de acessos móveis.
- Criptografia de dados sensíveis em repouso no RDS PostgreSQL.
- Painel administrativo simplificado para gestão de matrículas e emissão de certificados PDF.

## Passo a passo

### 1. Setup da Infraestrutura AWS

Provisionar ECS Fargate, RDS PostgreSQL e CloudFront para distribuição de mídia, herdando o modelo de baixo custo do Projeto LearnFast.

### 2. Integração do LRS Externo

Configurar o conector xAPI para enviar statements de progresso diretamente ao Learning Locker, reduzindo o overhead do banco de dados principal.

### 3. Implementação do Player de Mídia

Desenvolver player interativo compatível com SCORM 2004, HTML5, vídeos e PDFs, integrado ao CloudFront com cache agressivo para dispositivos móveis.

### 4. Mecanismo de Matrícula e Acesso

Criar painel administrativo para controle de acesso e carga manual de matrículas, sem necessidade de módulos complexos de e-commerce.

### 5. Gamificação e Certificados

Implementar regras simples de pontuação por conclusão de lições e geração automatizada de certificados em PDF sem validação pública.

### 6. Segurança e LGPD

Aplicar criptografia em repouso para dados de progresso dos alunos e estruturar a exclusão de dados pessoais conforme exigido pela LGPD.

## Decisões que a síntese já fecha (para PRD/SDD)

| Tema | Direção |
|------|---------|
| Tenant | single-tenant |
| xAPI / LRS | Learning Locker (externo) — não LRS embutido |
| Infra | ECS Fargate + RDS PostgreSQL + CloudFront |
| Matrícula / pago | admin + flag; sem e-commerce |
| Certificado | PDF download; sem verificação pública |
| LGPD | criptografia em repouso + exclusão de dados pessoais |
