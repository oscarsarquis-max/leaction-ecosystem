"""Cliente HTTP da Pluggy. Os testes injetam o transporte e não chamam a rede."""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

API = "https://api.pluggy.ai"
TIMEOUT = 8
KEY_LIFETIME = 2 * 60 * 60
KEY_SKEW = 5 * 60

_credentials = None


class PluggyError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code


def set_credentials(data):
    global _credentials
    _credentials = None if data is None else dict(data)


def load_credentials():
    """Lê o segredo uma vez. O valor não volta em log nem em resposta."""
    global _credentials
    if _credentials is not None:
        return _credentials
    if os.environ.get("ISA_PLUGGY_ENABLED") != "1":
        _credentials = {}
        return _credentials
    name = (os.environ.get("ISA_PLUGGY_SECRET_NAME") or "").strip()
    if not name:
        print("ISA bank secret missing", flush=True)
        _credentials = {}
        return _credentials
    try:
        import boto3
        raw = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-2").get_secret_value(SecretId=name)["SecretString"]
        data = json.loads(raw)
        _credentials = {
            "clientId": data["clientId"],
            "clientSecret": data["clientSecret"],
            "webhookSecret": data["webhookSecret"],
        }
    except Exception as exc:
        print("ISA bank secret " + type(exc).__name__, flush=True)
        _credentials = {}
    return _credentials


def enabled():
    return os.environ.get("ISA_PLUGGY_ENABLED") == "1" and bool(load_credentials().get("clientId"))


def _message(status):
    if status in (401, 403):
        return "A conexão com o serviço de bancos não foi aceita.", "unauthorized"
    if status == 404:
        return "Esta conexão não foi encontrada.", "not_found"
    return "Não foi possível falar com o serviço de bancos.", "http"


def _urllib_transport(method, url, headers, body):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8") or "{}")
    except HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        return exc.code, payload
    except (TimeoutError, URLError) as exc:
        if isinstance(exc, URLError) and not isinstance(getattr(exc, "reason", None), TimeoutError):
            raise PluggyError("Não foi possível falar com o serviço de bancos.", "network") from exc
        raise PluggyError("O banco demorou para responder. Tente de novo em alguns minutos.", "timeout") from exc


class Client:
    def __init__(self, credentials, transport=None, clock=None):
        self.credentials = credentials
        self.transport = transport or _urllib_transport
        self.clock = clock or time.time
        self._key = ""
        self._until = 0

    def api_key(self):
        now = self.clock()
        if self._key and now < self._until - KEY_SKEW:
            return self._key
        status, body = self._call("POST", "/auth", {"clientId": self.credentials.get("clientId"), "clientSecret": self.credentials.get("clientSecret")}, auth=False)
        if status != 200 or not body.get("apiKey"):
            message, code = _message(status)
            raise PluggyError(message, code)
        self._key = body["apiKey"]
        self._until = now + KEY_LIFETIME
        return self._key

    def connect_token(self, client_user_id, webhook_url):
        status, body = self._authed("POST", "/connect_token", {"options": {"clientUserId": client_user_id, "webhookUrl": webhook_url}})
        token = body.get("accessToken") or ""
        if status != 200 or not token:
            message, code = _message(status)
            raise PluggyError(message, code)
        return token

    def item(self, item_id):
        status, body = self._authed("GET", "/items/" + item_id, None)
        if status != 200:
            message, code = _message(status)
            raise PluggyError(message, code)
        return body

    def accounts(self, item_id):
        return self._pages("/accounts", {"itemId": item_id})

    def transactions(self, account_id, start, end):
        """Página o v2 e também aceita o formato com page/totalPages.

        from e to estão documentados na listagem por página. O guia manda o cursor.
        Se o corpo trouxer next, ele é seguido como veio.
        """
        return self._follow("/v2/transactions", {"accountId": account_id, "from": start, "to": end})

    def transactions_by_ids(self, account_id, identifiers):
        found = []
        chunk = []
        for identifier in identifiers:
            chunk.append(identifier)
            if len(chunk) == 500:
                found.extend(self._follow("/transactions", {"accountId": account_id, "ids": chunk}))
                chunk = []
        if chunk:
            found.extend(self._follow("/transactions", {"accountId": account_id, "ids": chunk}))
        return found

    def follow_link(self, url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "api.pluggy.ai":
            raise PluggyError("Não foi possível falar com o serviço de bancos.", "link")
        return self._follow(parsed.path + (("?" + parsed.query) if parsed.query else ""), None)

    def investments(self, item_id):
        return self._pages("/investments", {"itemId": item_id})

    def register_webhook(self, url, header_name, header_value):
        status, body = self._authed("POST", "/webhooks", {"event": "all", "url": url, "headers": {header_name: header_value}})
        if status not in (200, 201):
            message, code = _message(status)
            raise PluggyError(message, code)
        return body

    def delete_item(self, item_id):
        status, body = self._authed("DELETE", "/items/" + item_id, None)
        if status not in (200, 204, 404):
            message, code = _message(status)
            raise PluggyError(message, code)
        return status

    def _authed(self, method, path, body):
        return self._call(method, path, body, auth=True)

    def _call(self, method, path, body, auth):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            headers["X-API-KEY"] = self.api_key()
        url = path if path.startswith("https://") else API + path
        tried = False
        try:
            status, payload = self.transport(method, url, headers, body)
        except PluggyError as exc:
            if exc.code != "timeout":
                raise
            tried = True
            status, payload = self.transport(method, url, headers, body)
        if status >= 500 and not tried:
            status, payload = self.transport(method, url, headers, body)
        return status, payload if isinstance(payload, dict) else {}

    def _pages(self, path, query):
        page = 1
        found = []
        while page <= 40:
            params = dict(query)
            params["page"] = page
            params["pageSize"] = 500
            status, body = self._authed("GET", path + "?" + urlencode(params), None)
            if status != 200:
                message, code = _message(status)
                raise PluggyError(message, code)
            found.extend(body.get("results") or [])
            total = int(body.get("totalPages") or 1)
            if page >= total:
                return found
            page += 1
        raise PluggyError("Não foi possível falar com o serviço de bancos.", "pagina-limite")

    def _follow(self, path, query):
        found = []
        steps = 0
        if query is None:
            next_path = path
        else:
            params = dict(query)
            if isinstance(params.get("ids"), list):
                identifiers = params.pop("ids")
                encoded = urlencode(params)
                extra = "&".join("ids=" + item for item in identifiers)
                next_path = path + "?" + "&".join(part for part in (encoded, extra) if part)
            else:
                next_path = path + "?" + urlencode(params)
        while next_path and steps < 40:
            steps += 1
            status, body = self._authed("GET", next_path, None)
            if status != 200:
                message, code = _message(status)
                raise PluggyError(message, code)
            found.extend(body.get("results") or [])
            link = body.get("next") or ""
            if link:
                parsed = urlparse(link)
                if parsed.scheme and (parsed.scheme != "https" or parsed.netloc != "api.pluggy.ai"):
                    raise PluggyError("Não foi possível falar com o serviço de bancos.", "link")
                next_path = parsed.path + (("?" + parsed.query) if parsed.query else "") if parsed.scheme else link
                continue
            page = int(body.get("page") or 0)
            total = int(body.get("totalPages") or 0)
            if page and total and page < total and query is not None:
                params = dict(query)
                params["page"] = page + 1
                params["pageSize"] = 500
                next_path = path.split("?")[0] + "?" + urlencode(params)
                continue
            return found
        if steps >= 40 and next_path:
            raise PluggyError("Não foi possível falar com o serviço de bancos.", "pagina-limite")
        return found


def client(transport=None, clock=None):
    credentials = load_credentials()
    if not credentials.get("clientId"):
        raise PluggyError("A conexão com bancos ainda não está disponível.", "disabled")
    return Client(credentials, transport=transport, clock=clock)
