# PRM_007 — Adendo 002: migração para ingresso compartilhado

Data: 30/09/2026. Parecer e plano ajustado pelo analista. **Execução autorizada pelo proprietário**, que respondeu “autorizo” à migração para o `paneldx-alb` e à retirada do ALB dedicado após validação. Não iniciar PRM_008.

## Autorização registrada — prosseguir

O Cursor pode executar a sequência abaixo, incluindo associação de certificado, regras exclusivas do host ActionFinance no listener compartilhado, target group próprio, ajustes restritos de segurança/ECS, troca do alias e retirada dos recursos dedicados sem uso após sucesso comprovado. Não pedir novamente aprovação desse mesmo recorte. A autorização não abrange alterar rotas de outros produtos, excluir recursos compartilhados ou antecipar a retirada do caminho de reversão.

Se houver divergência material do plano ou interferência em outro produto, apresentar a diferença antes de prosseguir nessa parte; continuar o trabalho independente. Copiar este adendo atualizado para documents/prompts e registrar a autorização no DEP_001 e no relatório do PRM_007. A autorização não significa que a migração já foi executada.

## Parecer

Recomendo o host ActionFinance no `paneldx-alb`, com target group próprio e preservação das rotas existentes. O DEP_001 §8 confirma viabilidade e identifica o conflito com `/api*` de prioridade 10. A faixa US$ 35–50/mês continua indicativa, não nova cotação nem teto garantido.

Corrigir dois pontos do plano antes de executar:

1. Registrar e validar targets no novo caminho **antes de trocar DNS**, e não depois como na sequência atual da §8.4.
2. Não existe pausa do ALB equivalente a parar EC2. Mantê-lo existente para rollback mantém cobrança. A economia recorrente depende de excluir o ALB dedicado ao final da transição verificada. Durante a janela de validação, mantê-lo operacional, não “desligado mas existente”.

Os US$ 29,57 do plano incluem reserva de US$ 5,84 para aproximadamente 1 LCU; não são medição da fatura atual. Pelas mesmas premissas, horas e dois IPv4 somam US$ 23,73/mês, mais LCU efetivamente consumida. Depois da migração, contabilizar também consumo incremental no ALB compartilhado.

## Execução autorizada

1. Registrar estado atual, digest ECR completo, DNS, targets, regras/prioridades, certificados e health dos hosts existentes. Confirmar estado Terraform/ownership e não importar nem assumir gestão integral do ALB compartilhado no state ActionFinance. Gerenciar somente recursos novos próprios e associações explicitamente previstas.
2. Preparar plano com novo TG de IPs, certificado SNI e regra de host **exato** `actionfinance.actionhub.com.br` com prioridade livre numericamente menor que 10. Uma regra de host cobrindo todos os caminhos pode encaminhar SPA e API ao mesmo TG; não criar duas regras redundantes sem necessidade. Revalidar prioridades no ambiente, sem presumir 3/4 livres.
3. Liberar a porta da tarefa a partir do security group do ALB compartilhado. Manter temporariamente o caminho antigo e sua permissão durante a reversão possível. Não alterar `/api*`, default actions ou certificados padrão dos demais produtos.
4. Associar o serviço ECS ao novo TG e manter o TG antigo operacional durante a transição, usando suporte a múltiplos TGs se compatível com o deployment controller atual. Não registrar IP efêmero manualmente como solução permanente. Conferir health de ambos e deployment estável.
5. Antes do DNS, testar o ALB novo preservando Host e SNI do ActionFinance: TLS sem ignorar validação, SPA/assets, API e início/retorno do fluxo OIDC quando viável. Fazer smoke checks não mutantes dos hosts legados e comparar regras. Não concluir login humano real a partir de health ou redirect.
6. Trocar somente alias de `actionfinance.actionhub.com.br`. Observar propagação/cache, erros, targets e rotas. Validar no host público cookies, CSRF, logout e login real com o proprietário; ninguém fornece senha/MFA no chat.
7. Se houver regressão, restaurar alias antigo enquanto o caminho dedicado está operacional; reverter somente recursos/associações novos do ActionFinance. Não apagar compartilhados.
8. Após validação do novo caminho e período de observação/propagação documentado, retirar TG antigo da associação ECS e excluir **somente** ALB/listener/TG/SG dedicados que ficaram sem uso. Inspecionar plano destrutivo restrito antes de aplicar; preservar ACM reutilizado, serviço ECS, banco, logs, secrets, Cognito e ALB compartilhado. A concordância com este adendo cobre essa retirada condicionada ao sucesso; não requer nova confirmação para cada recurso da lista prevista.
9. Registrar instante de exclusão e estado final. Depois da retirada, rollback não é simples troca de DNS: requer reconstruir caminho anterior a partir de IaC. Documentar isso com clareza. Não manter ALB dedicado cobrando indefinidamente sob a descrição de recurso desligado.

## Entrega

Atualizar DEP_001 §8 com esta ordem, regras definitivas, custo indicativo corrigido e reversão em duas fases. Adicionar evidências ao REV_007_ADENDO_001 ou adendo vinculado, separando fatos de estimativas. Publicação só é concluída após login humano e condições operacionais do PRM_007, incluindo restore isolado ainda pendente.

Preservar login `admin@actionhub.com.br`, contato `oscar@oscarsarquis.com.br`, Loja de Pães sem CNPJ. Sem integração financeira, alterações ao módulo Pay, commit/push Git ou novo ciclo. Não enviar mensagem para solicitar aprovação em outro canal; o proprietário decide nesta conversa e encaminha a orientação ao executor.

Referências: [ECS com múltiplos target groups](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/register-multiple-targetgroups.html); [exclusão do ALB e encerramento de sua cobrança](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-delete.html).
