# Terraform enterprise — ECS / ALB / RDS (futuro)

**Não executar `terraform apply` neste perfil** durante homologação/piloto (ADR-010).

Arquitetura alvo de escala: ECS Fargate + ALB + RDS + NAT + autoscaling.

Homologação atual: [`../terraform-lightsail/`](../terraform-lightsail/).
