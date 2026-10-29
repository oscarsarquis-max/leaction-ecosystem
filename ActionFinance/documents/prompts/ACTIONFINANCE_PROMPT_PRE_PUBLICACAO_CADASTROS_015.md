# Parecer de interface e preparação operacional dos cadastros

Documento novo e independente para o Cursor. ACTIONFINANCE_PROMPT_PRE_PUBLICACAO_CADASTROS_015. Data 05/10/2026.

## Decisão do analista

Considero atendidas as pendências de interface do recorte 014, no alcance da candidata local e das evidências inspecionadas. Os cartões de importação mostram linha, documento, classificação, motivo e resultado; as caixas de documento estão alinhadas na captura desktop. Não reabrir o desenho nem iniciar outra reformulação.

Este parecer não representa aceite integral do produto pelo proprietário nem autorização para publicar ou migrar o RDS. Os requisitos operacionais de rollback e cópia restaurada permanecem pendentes, separados da interface.

## Base e limites da revisão

Foram lidos o relatório 014, identidade-candidata.json, os trechos de captura referentes à confirmação, repetição e consulta posterior, e o procedimento rehearse-isolated-restore-014.ps1. Foram abertas 360-importacao-mista-previa.png, 360-importacao-mista-confirmada.png e 1280-documento-cnpj.png. O analista não executou novamente os testes nem acessou produção.

O script consulta a lista após repetir a confirmação e exige totalItems=1. Isso sustenta a prova descrita de ausência de duplicação, além do contador retornado pelo lote. A recarga real com reautenticação está documentada; não equivale a provar restauração automática do destino após login produtivo.

A verificação de viewport 640 comprova responsividade em 640 pixels CSS. Não descrevê-la como execução de zoom real de 200% no navegador. Corrigir a redação da evidência; não reiniciar a aprovação visual por essa diferença. Se mantiver a afirmação de zoom real, executar essa verificação e registrar o método.

## Identificar a candidata que será ensaiada

HEAD d69e0f4e mais working tree e versão genérica 0.1.0 não identificam de forma imutável o conjunto testado. Registrar commit próprio das alterações pertinentes ou manifesto de arquivos e hashes que permita reproduzir exatamente a candidata, sem incluir segredos nem alterações alheias. Registrar migrations V14–V19, build frontend/backend, imagem e digest quando houver. Não publicar no origin nesta etapa.

## Provar rollback em ambiente isolado

Resolver a identidade exata da versão anterior efetivamente publicada. actionfinance-web:11 é uma referência operacional; identificar a imagem e o digest associados. A imagem local actionfinance:sair-cognito-010-4e556ecd só serve como versão anterior se a equivalência ao artefato publicado for comprovada.

Executar a versão anterior contra banco descartável V19, com rede de saída para integrações desativada e sem credenciais produtivas. Conferir inicialização e Flyway, leitura, cadastro no formato legado e edição sem perda dos campos novos. Registrar o resultado real, inclusive eventual falha de validação de migrations. Não contornar validações para produzir sucesso aparente.

Baixar ou inspecionar uma imagem para o ensaio não significa substituir o serviço em produção. A restrição dos pedidos anteriores era não alterar a aplicação pública para testar rollback. Não usar essa restrição como motivo para deixar de preparar o ensaio local. Respeitar os controles de acesso disponíveis e relatar qualquer bloqueio concreto.

Se rollback direto de imagem for inviável, apresentar alternativa concreta, compatível e testada em isolado antes de propor publicação. Não tratar restore como alternativa automática: preservar quaisquer escritas posteriores e definir a recuperação sem perda é requisito separado.

## Preparar o ensaio em cópia restaurada

O arquivo rehearse-isolated-restore-014.ps1 imprime instruções e valida uma string de destino. Não executa dump, restore, migração nem comparação. Não apresentá-lo como ensaio concluído ou como verificação do destino real.

Preparar o procedimento executável e revisável para destino descartável, distinto do volume de desenvolvimento e do RDS produtivo. Verificar a identidade efetiva do banco de destino antes de escrever; uma URL sem rds.amazonaws.com não basta, pois pode existir alias ou túnel. Prever comparação antes/depois de IDs, vínculos, valores, quantidade de registros, permissões e cobertura de documentos. O ensaio deve usar os mesmos artefatos candidatos identificados acima.

Não obter ou restaurar dump produtivo neste pedido. Concluir primeiro tudo que pode ser feito com dados sintéticos e artefatos locais. Depois apresentar uma solicitação única e concreta ao proprietário para a cópia: origem exata, destino isolado, forma de acesso somente leitura, conteúdo necessário, proteção e retenção do dump, responsável, eventuais custos e operações previstas. Não pedir credenciais pelo chat. Não suspender o trabalho local independente dessa autorização.

## Entrega

Criar ACTIONFINANCE_REV_PRE_PUBLICACAO_CADASTROS_015, sem apagar ou substituir as provas anteriores. Apresentar apenas: identidade da candidata, resultado do rollback, procedimento de cópia pronto para revisão e autorização efetivamente necessária. Distinguir não executado, aprovado no ensaio e reprovado. Não atribuir autorização ausente ao proprietário nem inferir publicação do aceite técnico da interface.

Não modificar Pay, Spider, Panne, Cognito, lançamentos financeiros ou cadastros produtivos. Não migrar o RDS, restaurar produção, criar infraestrutura paga ou publicar imagens no serviço. As próximas decisões dizem respeito à preparação operacional; o desenho do recorte 014 fica encerrado salvo defeito novo demonstrado.
