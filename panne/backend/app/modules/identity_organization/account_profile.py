"""E-mail verificado da conta autenticada. Não lê o corpo livre do navegador."""

from __future__ import annotations

from typing import Protocol

from botocore.exceptions import BotoCoreError, ClientError


class AccountProfileError(Exception):
    def __init__(self, reason: str, *, unavailable: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.unavailable = unavailable


class AccountProfileSource(Protocol):
    def verified_email(self, access_token: str) -> str: ...


class CognitoAccountProfile:
    """GetUser com o access token já validado. O escopo admin do token autoriza a chamada."""

    def verified_email(self, access_token: str) -> str:
        import boto3

        try:
            profile = boto3.client("cognito-idp").get_user(AccessToken=access_token)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {
                "TooManyRequestsException",
                "InternalErrorException",
                "LimitExceededException",
                "ServiceUnavailable",
            }:
                raise AccountProfileError("provedor_indisponivel", unavailable=True) from None
            if code in {"NotAuthorizedException", "UserNotFoundException", "ForbiddenException"}:
                raise AccountProfileError("email_invalido") from None
            raise AccountProfileError("provedor_indisponivel", unavailable=True) from None
        except BotoCoreError:
            raise AccountProfileError("provedor_indisponivel", unavailable=True) from None
        attributes = {
            item.get("Name"): item.get("Value")
            for item in profile.get("UserAttributes", [])
            if isinstance(item, dict)
        }
        email = attributes.get("email")
        verified = attributes.get("email_verified")
        if not isinstance(email, str) or "@" not in email or " " in email or verified != "true":
            raise AccountProfileError("email_invalido")
        return email.strip().lower()


class UnverifiedAccountProfile:
    """Usado fora do Cognito. Não inventa e-mail a partir das claims."""

    def verified_email(self, access_token: str) -> str:
        raise AccountProfileError("email_invalido")
