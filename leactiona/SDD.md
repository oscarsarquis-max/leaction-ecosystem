# Software Design Document (SDD) - LEACTIONA.COM.BR

## 1. Stack Tecnológica
- **Backend**: Node.js com Fastify (leve, rápido e de baixo consumo de memória) escrito em TypeScript.
- **Banco de Dados**: PostgreSQL (RDS Aurora Serverless v2 ou db.t4g.micro para baixo custo) com Prisma ORM.
- **Frontend**: Next.js (React) exportado como SPA estático para máxima performance em dispositivos antigos, estilizado com TailwindCSS.
- **LRS (Learning Record Store)**: Integração com Learning Locker externo (instância compartilhada ou dedicada de baixo custo) para isolar logs de progresso detalhados.
- **Armazenamento e CDN**: AWS S3 para pacotes SCORM/H5P e mídias estáticas, distribuídos globalmente via AWS CloudFront com políticas agressivas de cache.
- **Geração de Certificados**: Biblioteca leve `pdfkit` rodando diretamente no backend para evitar overhead de navegadores headless.
- **Segurança**: Criptografia em nível de aplicação (AES-256-GCM) para dados pessoais (CPF, e-mail) antes de persistir no banco de dados.

## 2. Arquitetura do Sistema
O sistema adota uma arquitetura monolítica modular single-tenant para simplificar a infraestrutura e manter o custo de operação extremamente baixo. O frontend estático é servido diretamente pelo CloudFront, reduzindo a carga no servidor backend.

Quando um aluno interage com um pacote SCORM ou player de vídeo, o frontend envia os statements xAPI diretamente para o LRS externo (Learning Locker). O backend do LMS consome periodicamente esses dados ou recebe webhooks do LRS para atualizar o progresso local de forma assíncrona. O player de vídeo customizado encapsula os players do YouTube e Vimeo, injetando uma camada DOM interativa para perguntas e notas em timestamps específicos, sem carregar scripts pesados de terceiros.

## 3. Modelo de Dados
O modelo de dados é projetado para PostgreSQL e mapeado via Prisma ORM:

- **User**: Armazena dados cadastrais criptografados (nome, e-mail, CPF), senha (hash bcrypt) e o papel de acesso (ADMIN, TEACHER, STUDENT).
- **Course**: Cadastro de cursos com flags de controle (is_free, is_active).
- **Module**: Organização sequencial de módulos dentro de um curso.
- **Lesson**: Unidades de conteúdo vinculadas a um módulo, contendo o tipo de mídia (VIDEO, AUDIO, PDF, SCORM, H5P) e a URL do recurso.
- **Enrollment**: Tabela de ligação entre User e Course, contendo a flag crítica `is_paid_access`, progresso percentual, nota média e status de conclusão.
- **GamificationProfile**: Pontuação acumulada e ranking do aluno.
- **Badge**: Cadastro de conquistas disponíveis.
- **UserBadge**: Registro de conquistas desbloqueadas pelos alunos.

## 4. Contratos de API / Componentes
- **POST /api/v1/auth/login**: Autenticação de usuários com retorno de token JWT.
- **GET /api/v1/courses**: Listagem de cursos disponíveis (filtrados por acesso gratuito ou pago baseado no perfil do aluno logado).
- **GET /api/v1/lessons/{id}**: Retorna os detalhes da lição e gera URLs assinadas do S3/CloudFront para consumo seguro de mídias.
- **POST /api/v1/lessons/{id}/complete**: Endpoint para registrar a conclusão manual de uma lição ou atualização via sincronização xAPI.
- **GET /api/v1/certificates/{courseId}/download**: Valida os requisitos de conclusão (100% progresso e nota >= 70%) e gera o PDF do certificado em tempo de execução para download direto.
- **POST /api/v1/admin/enrollments**: Permite ao administrador matricular alunos manualmente e definir a flag `is_paid_access`.
- **DELETE /api/v1/admin/users/{id}**: Executa a exclusão física dos dados pessoais do aluno em conformidade com a LGPD, anonimizando estatísticas de progresso.
