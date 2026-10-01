"use strict";

/**
 * Spider sandbox Monitor — viewer-request OIDC (Cognito).
 * Tokens stay in HttpOnly cookies. Config is baked at publish time.
 * Do not log tokens, codes, cookies, nonce or state.
 */

const crypto = require("crypto");
const https = require("https");
const { URL, URLSearchParams } = require("url");

const CONFIG = {
  poolId: "__POOL_ID__",
  clientId: "__CLIENT_ID__",
  issuer: "__ISSUER__",
  cognitoDomain: "__COGNITO_DOMAIN__",
  monitorHost: "__MONITOR_HOST__",
  apexHost: "__APEX_HOST__",
  group: "__GROUP__",
  credentialRef: "__CREDENTIAL_REF__",
  sessionSeconds: 3600,
  stateSecret: "__STATE_SECRET__",
};

const COOKIE_ID = "__Host-SpiderId";
const COOKIE_STATE = "__Host-SpiderSt";
const REQUIRED_GROUP = CONFIG.group;
const JWKS_PATH = `/${CONFIG.poolId}/.well-known/jwks.json`;
const JWKS_HOST = CONFIG.issuer.replace("https://", "").split("/")[0];

let jwksCache = { keys: [], exp: 0 };

function logEvent(event, category) {
  const payload = category ? { event, category } : { event };
  console.log(JSON.stringify(payload));
}

function base64url(buf) {
  return Buffer.from(buf)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function b64urlJson(value) {
  return JSON.parse(Buffer.from(value, "base64url").toString("utf8"));
}

function parseCookies(headerValue) {
  const out = {};
  String(headerValue || "")
    .split(";")
    .forEach((part) => {
      const idx = part.indexOf("=");
      if (idx < 1) return;
      const name = part.slice(0, idx).trim();
      out[name] = decodeURIComponent(part.slice(idx + 1).trim());
    });
  return out;
}

function cookieHeader(name, value, maxAge) {
  const parts = [
    `${name}=${encodeURIComponent(value)}`,
    "Path=/",
    "Secure",
    "HttpOnly",
    "SameSite=Lax",
  ];
  if (maxAge === 0) {
    parts.push("Max-Age=0");
    parts.push("Expires=Thu, 01 Jan 1970 00:00:00 GMT");
  } else if (typeof maxAge === "number") {
    parts.push(`Max-Age=${maxAge}`);
  }
  return parts.join("; ");
}

function clearCookie(name) {
  return cookieHeader(name, "", 0);
}

function hostOf(request) {
  const header = request.headers.host && request.headers.host[0];
  return header ? header.value.split(":")[0].toLowerCase() : "";
}

function headerValue(request, name) {
  const item = request.headers[name] && request.headers[name][0];
  return item ? item.value : "";
}

function safeReturnTo(value) {
  if (!value) return "/";
  const raw = String(value);
  if (raw.charAt(0) !== "/" || raw.charAt(1) === "/") return "/";
  if (raw.indexOf("\\") !== -1 || raw.indexOf("://") !== -1) return "/";
  if (raw.indexOf("\n") !== -1 || raw.indexOf("\r") !== -1) return "/";
  return raw.split("?")[0].split("#")[0] || "/";
}

function rewriteUri(uri) {
  if (uri === "/" || uri === "") return "/index.html";
  if (uri.indexOf(".") === -1) return "/index.html";
  return uri;
}

function isAuthPath(uri) {
  return uri === "/oauth/callback" || uri === "/logout" || uri === "/logged-out";
}

function isConsolePath(uri) {
  return uri.indexOf("/v1/console") === 0 || uri.indexOf("/v1/canonical") === 0;
}

function unauthorizedApi() {
  return response(
    401,
    null,
    [clearCookie(COOKIE_STATE)],
    JSON.stringify({
      title: "Unauthorized",
      status: 401,
      detail: "A sessão do Monitor é obrigatória para consultar a engine.",
    }),
    "application/problem+json",
  );
}

function queryMap(querystring) {
  const params = new URLSearchParams(querystring || "");
  const out = {};
  params.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

function signState(payload) {
  const body = base64url(Buffer.from(JSON.stringify(payload)));
  const mac = crypto.createHmac("sha256", CONFIG.stateSecret).update(body).digest();
  return `${body}.${base64url(mac)}`;
}

function readState(token) {
  if (!token || token.indexOf(".") < 0) return null;
  const [body, mac] = token.split(".");
  const expected = base64url(crypto.createHmac("sha256", CONFIG.stateSecret).update(body).digest());
  const left = Buffer.from(mac || "", "utf8");
  const right = Buffer.from(expected, "utf8");
  if (left.length !== right.length || !crypto.timingSafeEqual(left, right)) return null;
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8"));
    if (!payload || !payload.state || !payload.nonce || !payload.exp) return null;
    if (payload.exp < Math.floor(Date.now() / 1000)) return null;
    return payload;
  } catch (_err) {
    return null;
  }
}

function randomUrl(bytes) {
  return base64url(crypto.randomBytes(bytes));
}

function pkceChallenge(verifier) {
  return base64url(crypto.createHash("sha256").update(verifier).digest());
}

function httpsJson(method, urlString, body, extraHeaders) {
  return new Promise((resolve, reject) => {
    const url = new URL(urlString);
    const payload = body == null ? "" : body;
    const headers = Object.assign(
      {
        "content-type": "application/x-www-form-urlencoded",
        accept: "application/json",
      },
      extraHeaders || {},
    );
    if (payload) headers["content-length"] = Buffer.byteLength(payload);
    const req = https.request(
      {
        hostname: url.hostname,
        path: `${url.pathname}${url.search}`,
        method,
        headers,
        timeout: 4000,
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          if (res.statusCode < 200 || res.statusCode >= 300) {
            reject(new Error(`upstream_${res.statusCode}`));
            return;
          }
          if (!raw) {
            resolve({});
            return;
          }
          try {
            resolve(JSON.parse(raw));
          } catch (_err) {
            reject(new Error("upstream_json"));
          }
        });
      },
    );
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("upstream_timeout")));
    if (payload) req.write(payload);
    req.end();
  });
}

async function loadJwks() {
  if (jwksCache.keys.length && jwksCache.exp > Date.now()) return jwksCache.keys;
  const keys = await new Promise((resolve, reject) => {
    const req = https.request(
      {
        hostname: JWKS_HOST,
        path: JWKS_PATH,
        method: "GET",
        headers: { accept: "application/json" },
        timeout: 4000,
      },
      (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          try {
            const parsed = JSON.parse(Buffer.concat(chunks).toString("utf8"));
            resolve(parsed.keys || []);
          } catch (err) {
            reject(err);
          }
        });
      },
    );
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("jwks_timeout")));
    req.end();
  });
  jwksCache = { keys, exp: Date.now() + 300000 };
  return keys;
}

function verifyJwt(token, keys, expectedNonce) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) throw new Error("malformed");
  const header = b64urlJson(parts[0]);
  const payload = b64urlJson(parts[1]);
  if (header.alg !== "RS256") throw new Error("alg");
  const jwk = keys.find((item) => item.kid === header.kid);
  if (!jwk) throw new Error("kid");
  const key = crypto.createPublicKey({ key: jwk, format: "jwk" });
  const ok = crypto.verify(
    "RSA-SHA256",
    Buffer.from(`${parts[0]}.${parts[1]}`),
    key,
    Buffer.from(parts[2], "base64url"),
  );
  if (!ok) throw new Error("sig");
  const now = Math.floor(Date.now() / 1000);
  if (!payload.exp || payload.exp < now) throw new Error("expired");
  if (payload.iss !== CONFIG.issuer) throw new Error("iss");
  if (payload.aud !== CONFIG.clientId && payload.client_id !== CONFIG.clientId) throw new Error("aud");
  if (payload.token_use && payload.token_use !== "id") throw new Error("token_use");
  if (expectedNonce && payload.nonce !== expectedNonce) throw new Error("nonce");
  return payload;
}

function groupsOf(payload) {
  const value = payload["cognito:groups"];
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return [value];
  return [];
}

function response(status, location, cookies, body, contentType) {
  const headers = {
    "cache-control": [{ key: "Cache-Control", value: "no-store" }],
  };
  if (location) headers.location = [{ key: "Location", value: location }];
  if (cookies && cookies.length) {
    headers["set-cookie"] = cookies.map((value) => ({ key: "Set-Cookie", value }));
  }
  if (contentType) headers["content-type"] = [{ key: "Content-Type", value: contentType }];
  return {
    status: String(status),
    statusDescription:
      status === 302
        ? "Found"
        : status === 301
          ? "Moved Permanently"
          : status === 403
            ? "Forbidden"
            : status === 401
              ? "Unauthorized"
              : "OK",
    headers,
    body: body || "",
  };
}

function htmlPage(title, message) {
  const safeTitle = title.replace(/[<>]/g, "");
  const safeMessage = message.replace(/[<>]/g, "");
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>${safeTitle}</title></head><body><h1>${safeTitle}</h1><p>${safeMessage}</p></body></html>`;
}

function authorizeRedirect(returnTo) {
  const state = randomUrl(32);
  const nonce = randomUrl(32);
  const verifier = randomUrl(48);
  const ticket = signState({
    state,
    nonce,
    verifier,
    returnTo: safeReturnTo(returnTo),
    exp: Math.floor(Date.now() / 1000) + 600,
  });
  const params = new URLSearchParams({
    client_id: CONFIG.clientId,
    response_type: "code",
    scope: "openid email",
    redirect_uri: `https://${CONFIG.monitorHost}/oauth/callback`,
    state,
    nonce,
    code_challenge: pkceChallenge(verifier),
    code_challenge_method: "S256",
  });
  logEvent("login_started");
  return response(302, `${CONFIG.cognitoDomain}/oauth2/authorize?${params}`, [
    cookieHeader(COOKIE_STATE, ticket, 600),
    clearCookie(COOKIE_ID),
  ]);
}

async function handleCallback(request) {
  const query = queryMap(request.querystring);
  const cookies = parseCookies(headerValue(request, "cookie"));
  const ticket = readState(cookies[COOKIE_STATE]);
  if (query.error) {
    logEvent("auth_failure", "idp_error");
    return response(
      403,
      null,
      [clearCookie(COOKIE_STATE)],
      htmlPage("Acesso negado", "A autenticação foi recusada."),
      "text/html; charset=utf-8",
    );
  }
  if (!ticket || !query.code || query.state !== ticket.state) {
    logEvent("auth_failure", query.state && ticket ? "state" : "callback");
    return response(
      403,
      null,
      [clearCookie(COOKIE_STATE)],
      htmlPage("Acesso negado", "O retorno de autenticação é inválido ou já foi usado."),
      "text/html; charset=utf-8",
    );
  }
  let tokens;
  try {
    tokens = await httpsJson(
      "POST",
      `${CONFIG.cognitoDomain}/oauth2/token`,
      new URLSearchParams({
        grant_type: "authorization_code",
        client_id: CONFIG.clientId,
        code: query.code,
        redirect_uri: `https://${CONFIG.monitorHost}/oauth/callback`,
        code_verifier: ticket.verifier,
      }).toString(),
    );
  } catch (_err) {
    logEvent("auth_failure", "token");
    return response(
      403,
      null,
      [clearCookie(COOKIE_STATE)],
      htmlPage("Acesso negado", "Não foi possível concluir a autenticação."),
      "text/html; charset=utf-8",
    );
  }
  let payload;
  try {
    const keys = await loadJwks();
    payload = verifyJwt(tokens.id_token, keys, ticket.nonce);
  } catch (err) {
    logEvent("auth_failure", err.message || "jwt");
    return response(
      403,
      null,
      [clearCookie(COOKIE_STATE)],
      htmlPage("Acesso negado", "A identidade recebida não pôde ser validada."),
      "text/html; charset=utf-8",
    );
  }
  if (!groupsOf(payload).includes(REQUIRED_GROUP)) {
    logEvent("auth_failure", "group");
    return response(
      403,
      null,
      [clearCookie(COOKIE_STATE), clearCookie(COOKIE_ID)],
      htmlPage("Acesso negado", "Esta identidade não pertence ao grupo autorizado do Monitor."),
      "text/html; charset=utf-8",
    );
  }
  logEvent("login_completed");
  return response(302, `https://${CONFIG.monitorHost}${safeReturnTo(ticket.returnTo)}`, [
    cookieHeader(COOKIE_ID, tokens.id_token, CONFIG.sessionSeconds),
    clearCookie(COOKIE_STATE),
  ]);
}

function handleLogout() {
  logEvent("logout");
  const params = new URLSearchParams({
    client_id: CONFIG.clientId,
    logout_uri: `https://${CONFIG.monitorHost}/logged-out`,
  });
  return response(302, `${CONFIG.cognitoDomain}/logout?${params}`, [
    clearCookie(COOKIE_ID),
    clearCookie(COOKIE_STATE),
  ]);
}

function handleLoggedOut() {
  return authorizeRedirect("/");
}

async function requireSession(request) {
  const cookies = parseCookies(headerValue(request, "cookie"));
  const token = cookies[COOKIE_ID];
  const uri = request.uri.split("?")[0];
  if (!token) {
    logEvent("auth_failure", "anonymous");
    return isConsolePath(uri) ? unauthorizedApi() : authorizeRedirect(request.uri);
  }
  try {
    const keys = await loadJwks();
    const payload = verifyJwt(token, keys);
    if (!groupsOf(payload).includes(REQUIRED_GROUP)) {
      logEvent("auth_failure", "group");
      return response(
        403,
        null,
        [clearCookie(COOKIE_ID)],
        htmlPage("Acesso negado", "Esta identidade não pertence ao grupo autorizado do Monitor."),
        "text/html; charset=utf-8",
      );
    }
    return payload;
  } catch (err) {
    logEvent("auth_failure", err.message === "expired" ? "expired" : err.message || "jwt");
    return isConsolePath(uri) ? unauthorizedApi() : authorizeRedirect(request.uri);
  }
}

async function handle(event) {
  const request = event.Records[0].cf.request;
  const host = hostOf(request);
  if (host === CONFIG.apexHost) {
    return response(301, `https://${CONFIG.monitorHost}${request.uri}`);
  }
  const uri = request.uri.split("?")[0];
  if (uri === "/oauth/callback") {
    return handleCallback(request);
  }
  if (uri === "/logout") {
    return handleLogout();
  }
  if (uri === "/logged-out") {
    return handleLoggedOut();
  }
  const session = await requireSession(request);
  if (session && session.status) return session;
  if (isConsolePath(uri)) {
    request.headers["x-spider-credential-ref"] = [
      { key: "X-Spider-Credential-Ref", value: CONFIG.credentialRef },
    ];
    request.headers.authorization = [{ key: "Authorization", value: `Bearer ${parseCookies(headerValue(request, "cookie"))[COOKIE_ID]}` }];
    return request;
  }
  if (!isAuthPath(uri)) {
    request.uri = rewriteUri(uri);
  }
  return request;
}

exports.handler = async (event) => handle(event);

exports._internal = {
  CONFIG,
  isConsolePath,
  safeReturnTo,
  rewriteUri,
  signState,
  readState,
  verifyJwt,
  groupsOf,
  parseCookies,
  pkceChallenge,
  setJwksCache(keys) {
    jwksCache = { keys, exp: Date.now() + 300000 };
  },
};
