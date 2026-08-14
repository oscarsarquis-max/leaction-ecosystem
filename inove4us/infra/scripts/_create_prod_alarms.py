"""Cria SNS + alarmes CloudWatch de lançamento. Não imprime segredos."""
from __future__ import annotations

import json
import subprocess

AWS = r"C:\Program Files\Amazon\AWSCLIV2\aws.exe"
REGION = "us-east-2"
EMAIL = "suporte@leaction.com.br"
TOPIC_NAME = "leaction-prod-alerts"
ALB = "app/inove4us-prod/249a5e418be394dc"
TG = "targetgroup/inove4us-prod-tg/29948b76e5e907e5"
EC2 = "i-07f42e668d62038cd"


def run(args: list[str], region: str = REGION) -> str:
    cmd = [AWS, *args, "--region", region, "--output", "json"]
    return subprocess.check_output(cmd, text=True)


def main() -> None:
    topics = json.loads(run(["sns", "list-topics"]))["Topics"]
    arn = next((t["TopicArn"] for t in topics if t["TopicArn"].endswith(":" + TOPIC_NAME)), None)
    if not arn:
        arn = json.loads(run(["sns", "create-topic", "--name", TOPIC_NAME]))["TopicArn"]
        print("sns_created", arn)
    else:
        print("sns_exists", arn)

    subs = json.loads(run(["sns", "list-subscriptions-by-topic", "--topic-arn", arn])).get(
        "Subscriptions", []
    )
    if not any(s.get("Endpoint") == EMAIL for s in subs):
        run(["sns", "subscribe", "--topic-arn", arn, "--protocol", "email", "--notification-endpoint", EMAIL])
        print("sns_subscribe_pending_confirm", EMAIL)
    else:
        print("sns_subscribe_already", EMAIL)

    alarms = [
        {
            "AlarmName": "leaction-ec2-action-hub-cpu-alta",
            "AlarmDescription": "CPU do EC2 action_hub_prod (Hub+School) acima de 80% por 10 min.",
            "Namespace": "AWS/EC2",
            "MetricName": "CPUUtilization",
            "Dimensions": [{"Name": "InstanceId", "Value": EC2}],
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 80,
            "ComparisonOperator": "GreaterThanThreshold",
        },
        {
            "AlarmName": "leaction-ec2-action-hub-status-check",
            "AlarmDescription": "EC2 action_hub_prod falhou no status check da AWS.",
            "Namespace": "AWS/EC2",
            "MetricName": "StatusCheckFailed",
            "Dimensions": [{"Name": "InstanceId", "Value": EC2}],
            "Statistic": "Maximum",
            "Period": 60,
            "EvaluationPeriods": 2,
            "Threshold": 0,
            "ComparisonOperator": "GreaterThanThreshold",
        },
        {
            "AlarmName": "leaction-ecs-inove-cpu-alta",
            "AlarmDescription": "CPU do serviço ECS inove4us-prod acima de 80% por 10 min.",
            "Namespace": "AWS/ECS",
            "MetricName": "CPUUtilization",
            "Dimensions": [
                {"Name": "ClusterName", "Value": "inove4us-prod"},
                {"Name": "ServiceName", "Value": "inove4us-prod"},
            ],
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 80,
            "ComparisonOperator": "GreaterThanThreshold",
        },
        {
            "AlarmName": "leaction-ecs-inove-memoria-alta",
            "AlarmDescription": "Memória do serviço ECS inove4us-prod acima de 85% por 10 min.",
            "Namespace": "AWS/ECS",
            "MetricName": "MemoryUtilization",
            "Dimensions": [
                {"Name": "ClusterName", "Value": "inove4us-prod"},
                {"Name": "ServiceName", "Value": "inove4us-prod"},
            ],
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 85,
            "ComparisonOperator": "GreaterThanThreshold",
        },
        {
            "AlarmName": "leaction-alb-inove-host-nao-saudavel",
            "AlarmDescription": "ALB inove4us-prod com target unhealthy (health check falhou).",
            "Namespace": "AWS/ApplicationELB",
            "MetricName": "UnHealthyHostCount",
            "Dimensions": [
                {"Name": "LoadBalancer", "Value": ALB},
                {"Name": "TargetGroup", "Value": TG},
            ],
            "Statistic": "Maximum",
            "Period": 60,
            "EvaluationPeriods": 3,
            "Threshold": 0,
            "ComparisonOperator": "GreaterThanThreshold",
        },
    ]

    for spec in alarms:
        args = [
            "cloudwatch",
            "put-metric-alarm",
            "--alarm-name",
            spec["AlarmName"],
            "--alarm-description",
            spec["AlarmDescription"],
            "--namespace",
            spec["Namespace"],
            "--metric-name",
            spec["MetricName"],
            "--dimensions",
            json.dumps(spec["Dimensions"]),
            "--statistic",
            spec["Statistic"],
            "--period",
            str(spec["Period"]),
            "--evaluation-periods",
            str(spec["EvaluationPeriods"]),
            "--threshold",
            str(spec["Threshold"]),
            "--comparison-operator",
            spec["ComparisonOperator"],
            "--treat-missing-data",
            "notBreaching",
            "--alarm-actions",
            arn,
            "--ok-actions",
            arn,
        ]
        subprocess.check_call([AWS, *args, "--region", REGION])
        print("alarm", spec["AlarmName"])

    # Route53 health checks (API global us-east-1) para School e Inove /api/health
    existing = json.loads(
        subprocess.check_output(
            [AWS, "route53", "list-health-checks", "--output", "json"], text=True
        )
    )["HealthChecks"]
    wanted = {
        "school.inove4us.com.br": "leaction-school-api-health",
        "inove4us.com.br": "leaction-inove-api-health",
    }
    for fqdn, name in wanted.items():
        found = None
        for hc in existing:
            cfg = hc.get("HealthCheckConfig") or {}
            if cfg.get("FullyQualifiedDomainName") == fqdn and cfg.get("ResourcePath") == "/api/health":
                found = hc["Id"]
                break
        if not found:
            caller = f"{name}-2026-08-12"
            cfg = {
                "Type": "HTTPS",
                "FullyQualifiedDomainName": fqdn,
                "Port": 443,
                "ResourcePath": "/api/health",
                "RequestInterval": 30,
                "FailureThreshold": 3,
                "EnableSNI": True,
                "MeasureLatency": False,
            }
            created = json.loads(
                subprocess.check_output(
                    [
                        AWS,
                        "route53",
                        "create-health-check",
                        "--caller-reference",
                        caller,
                        "--health-check-config",
                        json.dumps(cfg),
                        "--output",
                        "json",
                    ],
                    text=True,
                )
            )
            found = created["HealthCheck"]["Id"]
            subprocess.check_call(
                [
                    AWS,
                    "route53",
                    "change-tags-for-resource",
                    "--resource-type",
                    "healthcheck",
                    "--resource-id",
                    found,
                    "--add-tags",
                    f"Key=Name,Value={name}",
                ]
            )
            print("healthcheck_created", name, found)
        else:
            print("healthcheck_exists", name, found)

        alarm_name = f"leaction-health-{fqdn.replace('.', '-')}"
        subprocess.check_call(
            [
                AWS,
                "cloudwatch",
                "put-metric-alarm",
                "--alarm-name",
                alarm_name,
                "--alarm-description",
                f"Health check HTTPS /api/health falhou em {fqdn}.",
                "--namespace",
                "AWS/Route53",
                "--metric-name",
                "HealthCheckStatus",
                "--dimensions",
                json.dumps([{"Name": "HealthCheckId", "Value": found}]),
                "--statistic",
                "Minimum",
                "--period",
                "60",
                "--evaluation-periods",
                "3",
                "--threshold",
                "1",
                "--comparison-operator",
                "LessThanThreshold",
                "--treat-missing-data",
                "breaching",
                "--alarm-actions",
                arn,
                "--ok-actions",
                arn,
                "--region",
                "us-east-1",
            ]
        )
        print("alarm", alarm_name)


if __name__ == "__main__":
    main()
