"""Provedor Cognito e SES. Não registra o código."""

from __future__ import annotations

import os
from urllib.parse import urlparse

import boto3

from app.modules.identity_organization.access_code import AccessCodeError, generate_access_code

_FROM = "nao-responda@panne.ia.br"
_EXPLANATION = (
    "Para o primeiro uso, o identificador do usuário é o e-mail cadastrado na contratação "
    "pela organização. O acesso é por um código enviado a este e-mail. Ele não expira, vale "
    "sempre exceto quando solicitada a sua alteração ou por descontinuidade da relação contratual."
)


def _pool_id() -> str:
    path = urlparse(os.environ.get("PANNE_OIDC_ISSUER", "")).path.strip("/")
    if not path:
        raise AccessCodeError("emissor_ausente")
    return path


def _client(service: str):
    return boto3.client(service, region_name=os.environ.get("AWS_REGION", "us-east-2"))


class CognitoDirectory:
    def ensure_user(self, email: str) -> None:
        client = _client("cognito-idp")
        try:
            client.admin_get_user(UserPoolId=_pool_id(), Username=email)
            return
        except client.exceptions.UserNotFoundException:
            pass
        temporary = generate_access_code()
        client.admin_create_user(
            UserPoolId=_pool_id(),
            Username=email,
            MessageAction="SUPPRESS",
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=temporary,
        )

    def set_permanent_code(self, email: str, code: str) -> None:
        _client("cognito-idp").admin_set_user_password(
            UserPoolId=_pool_id(),
            Username=email,
            Password=code,
            Permanent=True,
        )

    def disable_user(self, email: str) -> None:
        _client("cognito-idp").admin_disable_user(UserPoolId=_pool_id(), Username=email)

    def sign_out(self, email: str) -> None:
        _client("cognito-idp").admin_user_global_sign_out(UserPoolId=_pool_id(), Username=email)


class SesMailer:
    def send_access_code(self, email: str, code: str, *, replacement: bool) -> None:
        if replacement:
            subject = "Novo código de acesso à Panne"
            intro = "A Panne emitiu um novo código de acesso. O código anterior deixou de valer."
        else:
            subject = "Seu código de acesso à Panne"
            intro = _EXPLANATION
        body = (
            f"{intro}\n\n"
            "Seu código de acesso à Panne:\n"
            f"{code}\n\n"
            "Use o mesmo código nas próximas entradas. Entrar não envia outro código. "
            "A sessão no navegador pode expirar; o código continua o mesmo."
        )
        self._send(email, subject, body)

    def send_change_confirmation(self, email: str, confirmation: str) -> None:
        body = (
            "A Panne recebeu um pedido para alterar o seu código de acesso. "
            "Se foi você, confirme com o código abaixo. Ele autoriza só esta troca e deixa de valer depois do uso.\n\n"
            f"{confirmation}\n\n"
            "Se não foi você, ignore esta mensagem. O código de acesso atual continua valendo."
        )
        self._send(email, "Confirme a alteração do código da Panne", body)

    def _send(self, email: str, subject: str, body: str) -> None:
        _client("sesv2").send_email(
            FromEmailAddress=_FROM,
            Destination={"ToAddresses": [email]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
                }
            },
        )
