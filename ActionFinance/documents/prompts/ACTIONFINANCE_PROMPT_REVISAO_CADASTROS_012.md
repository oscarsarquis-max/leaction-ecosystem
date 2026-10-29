# ActionFinance correção e comprovação dos cadastros antes da publicação

Identificador: ACTIONFINANCE_PROMPT_REVISAO_CADASTROS_012. Data: 05/10/2026. Destinatário: Cursor. Documento novo independente, sem alterar o prompt 011. Aceite e migração produtiva não concedidos.

## Base da revisão

O analista leu REV_REFORMULACAO_CADASTROS_011, PACOTE_CADASTROS_011, V14__counterparty_directory.sql e DocumentNumbers.java. Não executou testes nem verificou diretamente o RDS. Os achados abaixo distinguem fragilidades observadas no DDL/código de comportamentos da aplicação ainda a demonstrar.

## R1 Estado real e reversão

O pacote afirma RDS em V12 e V13 não migrada. Isso contradiz relatos anteriores de V13 publicada. Fazer levantamento somente leitura de versão/checksums Flyway no destino efetivo, identificando conta/região/banco sem expor credenciais. Corrigir pacote com evidência datada; não presumir o estado por documentação antiga.

O pacote propõe restaurar backup pré-migration como rollback inicial. Isso pode descartar escritas posteriores. Priorizar reversão de código compatível com schema expandido quando comprovadamente possível. Se restore for necessário, definir interrupção controlada, janela/RPO, captura de escritas posteriores, reconciliação e troca de destino; restaurar primeiro em banco isolado, nunca sobrescrever produção por rotina. Nenhuma autorização de restore produtivo concedida aqui.

O passo “rodar PartyDirectoryIT contra a cópia” precisa ser tecnicamente conferido: se o IT cria seu próprio Testcontainer, não prova a cópia restaurada. Distinguir teste em container de ensaio de upgrade/restore com conexão explícita ao destino isolado. Demonstrar invariantes de títulos e vínculos antes/depois, grants e compatibilidade da imagem anterior. Não editar migration já aplicada em ambiente compartilhado; verificar histórico antes de escolher correção de V14/V15 ou migration incremental posterior.

## R2 Documento fiscal

DocumentNumbers.java aceita CNPJ por regex [A-Z0-9]{14} e CPF apenas por comprimento de 11 dígitos. Não há cálculo de dígitos verificadores nesse arquivo. O CNPJ alfanumérico tem 12 caracteres iniciais alfanuméricos e dois verificadores numéricos; não aceitar letras nas duas posições finais.

Fonte oficial consultada: https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf e documentação em https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj . Implementar validação oficial de formato/DV compatível com CNPJ numérico e alfanumérico e CPF, com vetores confiáveis. Validade matemática não prova existência/titularidade.

A normalização atual remove qualquer caractere não alfanumérico, podendo converter entrada malformada em outra identidade. Aceitar somente pontuação/espaçamento de apresentação previstos, recusando conteúdo estranho sem “corrigir” silenciosamente. Definir regras de OTHER por país/tipo sem colapsar documentos distintos indiscriminadamente. Validar país, coerência de tipo e person_kind; impedir combinações contraditórias ou mantê-las explicitamente pendentes conforme regra documentada.

Cadastro sem documento continua permitido. Documento inválido deve ser corrigido/removido ou ficar em revisão de importação; não receber aparência de validado. Atualizar testes que hoje aceitem valores estruturalmente inválidos.

## R3 Integridade entre fornecedor, unidade e endereço

Na V14 o endereço referencia counterparty_id e unit_id por FKs separadas. Isso garante mesma empresa, mas não que a unidade pertença à mesma contraparte do endereço. Fechar essa integridade com chave composta apropriada e validação no serviço. Provar rejeição de endereço da pessoa A ligado à unidade da pessoa B dentro da MESMA empresa, além do isolamento entre empresas.

Revisar os demais vínculos, incluindo match_counterparty_id da linha de importação, que no DDL lido não tem FK para contraparte. Identificadores de referência precisam de escopo e propriedade verificáveis, não apenas UUID sintaticamente válido. Não afirmar exploração pública sem teste; demonstrar integridade de banco e API.

## R4 Unicidade e identidade externa

counterparty_external_identity tem connection_key nullable e UNIQUE convencional incluindo esse campo. Conferir e corrigir a garantia de unicidade quando a conexão é nula: o contrato deve definir uma conexão não nula ou semântica de nulos que impeça repetição da identidade. Testar duas inserções concorrentes com mesma origem/ID e connection_key ausente, além de presente.

Documento da pessoa e documento da unidade têm índices separados; o de unidade ainda exclui inativas. Definir a autoridade de identidade para impedir que o mesmo estabelecimento seja associado indevidamente a duas pessoas, inclusive pessoa versus unidade ou reativação. Se documento da matriz puder aparecer tanto na pessoa como na unidade principal, esse espelhamento deve ser explícito e restrito à mesma entidade, não uma duplicidade livre. Provar casos cruzados e conflitos na importação.

Não fundir matriz/filiais automaticamente por nome ou raiz sem vínculo comprovado. Preservar identificação específica do estabelecimento na origem e nos futuros títulos/compras: agregar pessoa não pode apagar qual filial forneceu. Registrar a decisão de modelo e sua limitação atual antes da integração Panne.

## R5 Provas de interface e importação

O relatório descreve reutilização de classes CSS e breakpoints, mas isso não demonstra aparência ou jornada no browser. Produzir e inspecionar telas reais locais com backend/Postgres: lista, cadastrar sem busca prévia, cadastro completo/incompleto, detalhe, duplicidade, unidade/endereço, importação e erros, em 360/768/1280. Comparar com a proposta visual sem transportar suas imprecisões conhecidas. Sem dados pessoais produtivos nas capturas.

Executar os testes relevantes com relatório quantitativo, exit e ambiente. Demonstrar importação por linha com reenvio, concorrência, atualização entre prévia/confirmação, documento ausente e repetição de arquivo após confirmação. Hash do arquivo sozinho não resolve todos esses casos. Se linha sem identidade forte não puder ser deduplicada com certeza, exigir revisão explícita; não fundir por nome.

Comprovar compatibility do cadastro rápido no título, viewer, escopo, inativação referenciada e histórico. Campos novos não podem desaparecer silenciosamente numa edição pelo endpoint legado. Rever mascaramento de documento em lista, candidatos, detalhes, erros e resultados de importação, não somente no GET de detalhe.

## Entrega e limites

Criar ACTIONFINANCE_REV_REVISAO_CADASTROS_012.md com cada achado, correção/decisão, prova e limitação. Copiar este prompt como documento novo para documents/prompts. Atualizar o pacote de publicação com referência à nova revisão e evidências, preservando histórico.

Entregar candidata local revisável e plano de migração comprovado em destino isolado. Não aplicar migrations/importações no RDS produtivo, ativar conector Panne, executar pagamento ou alterar Pay/Spider por este prompt. Aceite do desenho e publicação continuam pendentes. Pendências dos demais ciclos permanecem separadas.
