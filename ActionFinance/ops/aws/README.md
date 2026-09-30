# Pacote de publicação ActionFinance (não aplicado)

Destino pretendido: `https://actionfinance.actionhub.com.br`.

As definições parametrizadas estão em `ops/aws/terraform/`. **Não foram aplicadas.** Não importam state de Hub, Spider, Panne ou School. Placeholders não representam recursos existentes.

## Arquitetura escolhida

TLS termina no **ALB em `us-east-2`**. Não há CloudFront neste recorte: o certificado ACM exigido é regional em `us-east-2` para o listener 443. Um certificado de CloudFront em `us-east-1` só seria necessário se o ingresso passasse a ser CloudFront; isso não foi adotado.

WAF não substitui o IdP. O IdP autentica pessoas; WAF filtra rede. Nenhum dos dois foi ativado.

O processo da aplicação não confia em `X-Forwarded-*` (`server.forward-headers-strategy=none`). Origem pública e callback OIDC vêm só da configuração. O serviço deve ser alcançável apenas pelo ALB (`security_group` do task aceita só o ALB).

## Novo versus reutilizado (referência da conta observada `253137917703`)

| Recurso | Decisão deste pacote |
|---|---|
| Conta / região | Referência documental: mesma conta, compute `us-east-2` |
| VPC / subnets | Reutilizar VPC corporativa se o proprietário apontar IDs; senão criar depois. Variáveis obrigatórias, sem default real |
| ALB / target group / listener 443 | **Novo**, exclusivo ActionFinance |
| ECS cluster / service / task | **Novo** `actionfinance` |
| ECR | Repositório `actionfinance` novo ou vazio já reservado; sem push neste ciclo |
| RDS / Postgres | Banco e roles `actionfinance` isolados; não o volume da Spider nem Hub |
| Secrets Manager | Segredos OIDC e senhas só deste produto |
| CloudFront / WAF | Fora desta definição |
| Cookie | host-only do subdomínio; sem `Domain=actionhub.com.br` |

Validação local de sintaxe: `terraform fmt -check` e `terraform validate` no diretório, com `terraform.tfvars` preenchido pelo operador. Este ciclo não aplica.

## Ensaio HTTPS local (não é AWS)

`ops/compose/actionfinance-https-trial.yml` usa Postgres e IdP descartáveis em portas/volumes próprios. Não reutiliza 5433/5436/5439 nem volumes de outros produtos.
