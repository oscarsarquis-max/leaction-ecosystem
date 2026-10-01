# PRM_009 — Recomendação de execução do pacote revisado

Data: 01/10/2026.

## Autorização já concedida

O proprietário declarou nesta conversa: “tem minha autorizacao.” A autorização foi registrada para implantação pública do PRM_009, ações Git previstas e custo incremental estimado, após resolução e teste dos bloqueios do parecer. Ela permanece válida; não pedir outra confirmação para o mesmo escopo.

Corrigir no pacote os campos “Implantação autorizada: Não” e o pedido de autorização final. Registrar a autorização do proprietário separadamente desta recomendação técnica. Implantação executada, jornada pública validada e aceite do proprietário continuam pendentes até ocorrerem.

## Recomendação

Após leitura do pacote revisado e conferência pontual das referências de configuração e seleção da relação do Hub, recomendo prosseguir com a execução delimitada. Os testes e hashes do candidato são os apresentados pelo executor; não foram reexecutados pelo analista.

Executar o pacote revisado na infraestrutura existente: schema exclusivo de teste no PG Hub, nenhuma inserção em public.orders, flag própria do Finance com homolog=false, autorização do Monitor, regra SG /32 indicada, migrações V8–V12 e publicação coordenada. Sidecar, novos recursos faturáveis, dados reais da Loja e mensagens/convites permanecem fora da autorização.

## Cuidados de execução dentro do escopo

1. Preservar trabalho alheio. Criar a branch autorizada e conferir o diff integral contra a base: criar branch a partir do HEAD não remove commits anteriores nem mudanças locais de outros produtos. Construir/testar a partir do conjunto efetivamente incluído, registrar commit, hashes e digests publicados. Não usar artefato gerado de arquivos excluídos do commit como se fosse o mesmo candidato.
2. Na prova pública do Monitor, confirmar a cadeia de autenticação e o significado efetivo de owner:sandbox. Não apresentar principal compartilhado como identidade individual Cognito. O recorte de empresa deve valer em todos os canais publicados e não admitir acesso anônimo ou troca de ID. Se a topologia expuser bypass, corrigir antes de disponibilizar a integração.
3. Não esvaziar o secret obrigatório da tarefa AF para ensaiar indisponibilidade: o validador pode impedir o startup e afetar o produto inteiro. Usar falha restrita à integração/app de teste, preservando login e funcionalidades financeiras existentes. Não derrubar engine compartilhada.
4. Rollback conserva dados e schema de teste; não executar o DROP SCHEMA opcional citado na tabela do pacote. Desabilitar integração e reverter componentes conforme necessidade. Não restaurar acesso amplo do Monitor ao voltar imagem: preservar barreira de acesso ou indisponibilizar a funcionalidade afetada.
5. Se um teste ou gate falhar, corrigir dentro do escopo ou reverter o componente afetado; não declarar sucesso nem contornar controles. Pedir decisão nova somente se for indispensável ampliar custo, infraestrutura, permissões ou uso de dados reais.

## Entrega exigida

Não parar na preparação ou no push: executar até a validação pública autorizada, salvo impedimento concreto. Entregar URLs públicas verificadas, empresa/ambiente de teste, execução nova iniciada no Finance, link correspondente no Monitor, correlação até o Hub e retorno persistido no Finance. Fornecer roteiro curto para o proprietário repetir, sem senhas, MFA ou tokens no chat.

Registrar testes de isolamento e integridade, versões finais, migrações e estado dos serviços. Não confundir a autorização de implantação com aceite do resultado.

Copiar este documento para documents/reviews, atualizar pacote e índice. PRM_007 continua com pendência separada; PRM_010 não emitido. O aceite final do proprietário depende da jornada pública funcionando.
