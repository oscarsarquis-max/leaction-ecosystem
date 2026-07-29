# Documento de Requisitos do Produto (PRD) — LEACTIONA.COM.BR

## 1. Visão Geral

### 1.1. Objetivo do Produto
O objetivo do projeto **LEACTIONA.COM.BR** é substituir a atual plataforma educacional baseada em Moodle por uma solução proprietária, leve, rápida e altamente responsiva. O sistema será focado na entrega de cursos multimídia com rastreamento detalhado de progresso via padrões SCORM 2004 (4ª edição) e xAPI, além de dinâmicas de gamificação.

A plataforma foi concebida sob uma arquitetura **single-tenant** (operação única para a própria academia) e otimizada para baixo custo de infraestrutura na AWS, garantindo excelente usabilidade mesmo em dispositivos móveis antigos e conexões limitadas (3G/4G).

### 1.2. Escopo do Produto (v1)
*   **Gestão de Aprendizado (LMS Core):** Cadastro manual de cursos, módulos, lições e controle de acessos baseado em papéis (RBAC).
*   **Rastreamento Avançado:** Integração com LRS externo (Learning Locker) para envio e consulta de statements xAPI e suporte a pacotes SCORM 2004.
*   **Player Multimídia Interativo:** Player leve para vídeos (YouTube/Vimeo) com suporte a camadas interativas (estilo H5P) e suporte a múltiplos formatos (MP4, MP3, PDF, HTML5).
*   **Gamificação:** Sistema de pontuação, conquistas (badges) e ranking de alunos.
*   **Certificados:** Geração automatizada de certificados simples em formato PDF para download.
*   **Controle de Acesso Simplificado:** Liberação de conteúdo gratuito/pago por meio de flag/status de matrícula (sem gateway de pagamento interno).
*   **Segurança e LGPD:** Criptografia de dados pessoais em repouso e conformidade com as diretrizes de privacidade.

### 1.3. Fora de Escopo (v1)
*   Migração ou importação automatizada de dados históricos do Moodle.
*   Gateway de pagamento, checkout, faturamento ou assinaturas recorrentes na plataforma.
*   Aplicativo móvel nativo (foco exclusivo em Web App responsivo).
*   Fóruns de discussão, comunidades ou comentários entre alunos.
*   Transmissões ao vivo (webinars) ou salas de aula virtuais síncronas.
*   Página pública de verificação de certificados por QR Code ou código de validação.
*   Arquitetura multi-tenant (isolamento de múltiplos clientes/escolas).

---

## 2. Público-alvo

### 2.1. Aluno (Consumidor Final)
*   **Perfil:** Profissionais e estudantes que buscam capacitação rápida.
*   **Necessidades:** Acesso rápido ao conteúdo em trânsito (via smartphones antigos em redes 3G/4G), interface limpa e sem distrações, feedback visual claro de progresso e gamificação.
*   **Comportamento:** Consome vídeos, áudios (podcasts), PDFs e pacotes interativos; realiza avaliações; acompanha sua pontuação no ranking e baixa seu certificado ao concluir o curso.

### 2.2. Administrador / Professor (Gestor da Operação)
*   **Perfil:** Gestores de conteúdo e administradores da academia.
*   **Necessidades:** Painel administrativo simplificado para cadastrar cursos e lições, matricular alunos manualmente (atribuindo flags de acesso pago/gratuito) e visualizar relatórios de progresso baseados nos dados do LRS.
*   **Comportamento:** Realiza o upload de mídias, configura regras de pontuação/badges, gerencia usuários e exporta relatórios de desempenho.

---

## 3. Regras de Negócio Core

### 3.1. Controle de Acesso e Matrícula (RBAC & Flags)
*   **RN01 - Papéis de Usuário:** O sistema deve suportar pelo menos três papéis distintos: `Administrador`, `Professor` e `Aluno`.
*   **RN02 - Liberação de Conteúdo:** A liberação de cursos pagos é controlada estritamente por uma flag lógica de matrícula (`is_paid_access: true/false`) associada ao vínculo do aluno com o curso. Não haverá processamento financeiro interno.
*   **RN03 - Conteúdo Gratuito:** Cursos ou lições marcados como `is_free: true` devem ser acessíveis por qualquer usuário cadastrado, independentemente de flags de pagamento.

### 3.2. Rastreamento xAPI e SCORM 2004
*   **RN04 - Desacoplamento de Logs:** Todos os eventos de progresso detalhado (statements xAPI) gerados pelos alunos ao interagir com pacotes SCORM ou mídias devem ser enviados diretamente ao LRS externo (Learning Locker) para evitar sobrecarga no banco de dados principal (RDS PostgreSQL).
*   **RN05 - Sincronização de Progresso:** O LMS deve consultar periodicamente ou via webhook o LRS para atualizar o status local de conclusão de lições e cursos na base de dados principal.

### 3.3. Player de Mídia e Interatividade
*   **RN06 - Player Distraction-Free:** O player interno deve encapsular vídeos do YouTube e Vimeo ocultando controles nativos, anúncios, sugestões de vídeos externos e links de compartilhamento.
*   **RN07 - Camadas Interativas:** O player deve permitir a sobreposição de elementos interativos (perguntas de múltipla escolha, notas de texto) em timestamps específicos do vídeo, simulando o comportamento do H5P.

### 3.4. Gamificação e Certificação
*   **RN08 - Regra de Pontuação:** O aluno acumula pontos ao concluir lições (X pontos) e ao atingir notas mínimas em avaliações (Y pontos). Esses pontos alimentam o ranking geral.
*   **RN09 - Emissão de Certificado:** O certificado em PDF simples é gerado automaticamente quando o progresso do curso atinge 100% e a nota média das avaliações for igual ou superior a 70% (configurável por curso).
*   **RN10 - Download Direto:** O certificado é disponibilizado exclusivamente como download de arquivo PDF estático para o aluno logado, sem geração de URL pública de validação.

### 3.5. Segurança e LGPD
*   **RN11 - Minimização de Dados:** Apenas dados estritamente necessários para a operação serão coletados (Nome, E-mail, CPF/Identificador, Progresso Acadêmico).
*   **RN12 - Direito ao Esquecimento:** O sistema deve fornecer uma rotina administrativa para anonimizar ou excluir permanentemente os dados pessoais de um aluno, mantendo apenas dados estatísticos anonimizados de progresso.

---

## 4. Casos de Uso / Jornadas

### 4.1. UC01: Aluno Consumindo Conteúdo Interativo (SCORM/xAPI)
*   **Atores:** Aluno.
*   **Pré-condições:** Aluno autenticado e matriculado no curso.
*   **Fluxo Principal:**
    1. O aluno acessa a página da lição contendo um pacote SCORM 2004.
    2. O LMS renderiza o pacote dentro de um iframe otimizado, inicializando a API de comunicação xAPI.
    3. O aluno interage com o conteúdo (avança slides, responde perguntas internas).
    4. A cada interação relevante, o player dispara um statement xAPI (ex: "João completou o slide 3") diretamente para o Learning Locker.
    5. Ao finalizar o pacote, o LRS registra o status de conclusão.
    6. O LMS detecta a conclusão, atualiza o progresso local do aluno para "Concluído" e concede os pontos correspondentes de gamificação.

### 4.2. UC02: Administração de Matrículas e Controle de Acesso
*   **Atores:** Administrador.
*   **Pré-condições:** Administrador autenticado no painel de controle.
*   **Fluxo Principal:**
    1. O administrador acessa a área de "Gestão de Alunos".
    2. Seleciona um aluno e clica em "Vincular Curso".
    3. Seleciona o curso desejado e define a flag de acesso (Pago ou Gratuito).
    4. Salva a operação.
    5. O sistema registra o vínculo no banco de dados local.
    6. O aluno recebe acesso imediato ao conteúdo restrito do curso na sua área logada.

### 4.3. UC03: Conclusão de Curso, Gamificação e Emissão de Certificado
*   **Atores:** Aluno.
*   **Pré-condições:** Aluno concluiu a última lição obrigatória do curso.
*   **Fluxo Principal:**
    1. O aluno finaliza a última atividade do curso.
    2. O sistema calcula a nota média das avaliações e valida o progresso (100%).
    3. O sistema dispara o gatilho de conquista: concede a badge "Mestre do Curso X" e adiciona 500 pontos ao perfil do aluno.
    4. O ranking de alunos é atualizado instantaneamente.
    5. Um botão "Baixar Certificado" é habilitado na interface do aluno.
    6. O aluno clica no botão e o sistema gera e inicia o download do PDF do certificado personalizado.

---

## 5. Critérios de Aceite

### 5.1. Desempenho e Otimização Móvel
*   **CA01:** O tamanho total da página inicial da área logada do aluno não deve exceder 1.5MB (incluindo assets estáticos), garantindo carregamento rápido em conexões 3G.
*   **CA02:** Todos os assets estáticos (CSS, JS, Imagens) devem ser servidos via AWS CloudFront com políticas de cache agressivas (mínimo de 30 dias para arquivos imutáveis).
*   **CA03:** A interface deve ser totalmente responsiva, obtendo pontuação mínima de 85/100 no Google Lighthouse (Mobile) para a categoria de Performance.

### 5.2. Integração com LRS e Rastreamento
*   **CA04:** Todo statement xAPI gerado deve ser transmitido de forma assíncrona para o Learning Locker em menos de 500ms após a ação do usuário, sem bloquear a interface do aluno.
*   **CA05:** Em caso de falha temporária de conexão com o LRS, o player deve reter os statements em `localStorage` e tentar reenviá-los assim que a conexão for restabelecida.

### 5.3. Segurança e LGPD
*   **CA06:** Todas as conexões devem ser forçadas via HTTPS (TLS 1.3).
*   **CA07:** Os dados pessoais sensíveis (como CPF e e-mail) devem ser criptografados em repouso no banco de dados RDS PostgreSQL utilizando criptografia AES-256.
*   **CA08:** A exclusão de um usuário pelo administrador deve remover fisicamente seus registros de identificação pessoal do banco de dados principal em até 24 horas, mantendo apenas registros de progresso totalmente anonimizados (sem chaves estrangeiras para o usuário excluído).
