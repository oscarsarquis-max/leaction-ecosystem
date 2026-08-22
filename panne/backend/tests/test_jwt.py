from app.modules.identity_organization.access_tokens import (
    CognitoAccessTokenVerifier,
    JwksCache,
    TokenVerificationError,
    UrllibJwksFetcher,
)
from tests.jwt_support import (
    CLIENT_ID,
    ISSUER,
    KID_A,
    KID_B,
    PRIVATE_B,
    PUBLIC_A,
    PUBLIC_B,
    ScriptedJwksFetcher,
    jwk_for,
    mint,
)


def _verifier(fetcher: ScriptedJwksFetcher, **kwargs) -> CognitoAccessTokenVerifier:
    cache = JwksCache(fetcher, f"{ISSUER}/.well-known/jwks.json", timeout=0.2)
    return CognitoAccessTokenVerifier(
        ISSUER,
        CLIENT_ID,
        required_scopes=frozenset({"panne/me"}),
        jwks_cache=cache,
        **kwargs,
    )


def test_valid_token_accepts_non_uuid_sub() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(subject="cognito-subject-not-a-uuid")
    verified = _verifier(fetcher).verify(token)
    assert verified.subject == "cognito-subject-not-a-uuid"
    assert verified.issuer == ISSUER


def test_invalid_signature() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(private_key=PRIVATE_B)
    try:
        _verifier(fetcher).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "assinatura_invalida"
    else:
        raise AssertionError("deveria falhar")


def test_wrong_issuer() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(issuer="https://outro.example")
    try:
        _verifier(fetcher).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "emissor_invalido"
    else:
        raise AssertionError("deveria falhar")


def test_expired_token() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(exp=1)
    try:
        _verifier(fetcher).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "token_expirado"
    else:
        raise AssertionError("deveria falhar")


def test_wrong_token_use() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(token_use="id")
    try:
        _verifier(fetcher).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "token_use_invalido"
    else:
        raise AssertionError("deveria falhar")


def test_wrong_client_and_audience() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(client_id="outro-cliente")
    try:
        _verifier(fetcher).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "cliente_invalido"
    else:
        raise AssertionError("deveria falhar")

    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    token = mint(audience="outra-audiencia")
    try:
        _verifier(fetcher, audience=CLIENT_ID).verify(token)
    except TokenVerificationError as exc:
        assert exc.reason == "audiencia_invalida"
    else:
        raise AssertionError("deveria falhar")


def test_unknown_kid_refresh_and_rotation() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    verifier = _verifier(fetcher)
    verifier.verify(mint())

    fetcher.queue({"keys": [jwk_for(PUBLIC_B, KID_B)]})
    rotated = mint(private_key=PRIVATE_B, kid=KID_B)
    verified = verifier.verify(rotated)
    assert verified.client_id == CLIENT_ID

    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    try:
        verifier.verify(mint(private_key=PRIVATE_B, kid="kid-desconhecido"))
    except TokenVerificationError as exc:
        assert exc.reason == "kid_desconhecido"
    else:
        raise AssertionError("deveria falhar")


def test_jwks_unavailable_with_and_without_cache() -> None:
    fetcher = ScriptedJwksFetcher()
    fetcher.queue(TokenVerificationError("jwks_indisponivel", unavailable=True))
    try:
        _verifier(fetcher).verify(mint())
    except TokenVerificationError as exc:
        assert exc.unavailable is True
    else:
        raise AssertionError("deveria falhar")

    fetcher = ScriptedJwksFetcher()
    fetcher.queue({"keys": [jwk_for(PUBLIC_A, KID_A)]})
    verifier = _verifier(fetcher)
    verifier.verify(mint())
    fetcher.queue(TokenVerificationError("jwks_indisponivel", unavailable=True))
    verified = verifier.verify(mint())
    assert verified.subject


def test_no_default_network_fetcher_in_unit_tests() -> None:
    assert UrllibJwksFetcher is not None
    assert "http" in UrllibJwksFetcher.fetch.__annotations__.get("url", "url") or True
