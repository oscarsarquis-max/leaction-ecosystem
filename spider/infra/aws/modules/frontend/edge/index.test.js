"use strict";

const assert = require("assert");
const crypto = require("crypto");
const { describe, it, before } = require("node:test");
const edge = require("./index.js");

function b64url(buf) {
  return Buffer.from(buf)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function signJwt(privateKey, header, payload) {
  const h = b64url(Buffer.from(JSON.stringify(header)));
  const p = b64url(Buffer.from(JSON.stringify(payload)));
  const sig = crypto.sign("RSA-SHA256", Buffer.from(`${h}.${p}`), privateKey);
  return `${h}.${p}.${b64url(sig)}`;
}

describe("spider monitor edge oidc", () => {
  const pair = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwk = pair.publicKey.export({ format: "jwk" });
  jwk.kid = "test-kid";
  jwk.use = "sig";
  jwk.alg = "RS256";

  before(() => {
    edge._internal.CONFIG.issuer = "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_test";
    edge._internal.CONFIG.clientId = "client-test";
    edge._internal.CONFIG.stateSecret = "state-secret-for-tests-32bytes-min";
    edge._internal.CONFIG.group = "spider-sandbox-operators";
    edge._internal.setJwksCache([jwk]);
  });

  it("blocks open redirects", () => {
    assert.strictEqual(edge._internal.safeReturnTo("https://evil.example"), "/");
    assert.strictEqual(edge._internal.safeReturnTo("//evil.example"), "/");
    assert.strictEqual(edge._internal.safeReturnTo("/console"), "/console");
    assert.strictEqual(edge._internal.safeReturnTo("/v1/canonical/executions"), "/v1/canonical/executions");
  });

  it("treats console and canonical API as session-bound API paths", () => {
    assert.strictEqual(edge._internal.isConsolePath("/v1/console/executions"), true);
    assert.strictEqual(edge._internal.isConsolePath("/v1/canonical/executions"), true);
    assert.strictEqual(edge._internal.isConsolePath("/assets/index.js"), false);
  });

  it("rewrites SPA routes and keeps hashed assets", () => {
    assert.strictEqual(edge._internal.rewriteUri("/"), "/index.html");
    assert.strictEqual(edge._internal.rewriteUri("/console"), "/index.html");
    assert.strictEqual(edge._internal.rewriteUri("/assets/index-abc.js"), "/assets/index-abc.js");
  });

  it("rejects tampered or expired state", () => {
    const token = edge._internal.signState({
      state: "abc",
      nonce: "n",
      verifier: "v",
      returnTo: "/",
      exp: Math.floor(Date.now() / 1000) + 60,
    });
    assert.ok(edge._internal.readState(token));
    assert.strictEqual(edge._internal.readState(token + "x"), null);
    const expired = edge._internal.signState({
      state: "abc",
      nonce: "n",
      verifier: "v",
      returnTo: "/",
      exp: Math.floor(Date.now() / 1000) - 10,
    });
    assert.strictEqual(edge._internal.readState(expired), null);
  });

  it("validates signature, issuer, audience, expiry and group", () => {
    const now = Math.floor(Date.now() / 1000);
    const valid = signJwt(
      pair.privateKey,
      { alg: "RS256", kid: "test-kid" },
      {
        iss: edge._internal.CONFIG.issuer,
        aud: "client-test",
        exp: now + 120,
        token_use: "id",
        nonce: "nonce-1",
        "cognito:groups": ["spider-sandbox-operators"],
      },
    );
    const payload = edge._internal.verifyJwt(valid, [jwk], "nonce-1");
    assert.ok(edge._internal.groupsOf(payload).includes("spider-sandbox-operators"));

    assert.throws(
      () =>
        edge._internal.verifyJwt(
          signJwt(
            pair.privateKey,
            { alg: "RS256", kid: "test-kid" },
            { iss: "https://evil", aud: "client-test", exp: now + 120, token_use: "id" },
          ),
          [jwk],
        ),
      /iss/,
    );
    assert.throws(
      () =>
        edge._internal.verifyJwt(
          signJwt(
            pair.privateKey,
            { alg: "RS256", kid: "test-kid" },
            { iss: edge._internal.CONFIG.issuer, aud: "other", exp: now + 120, token_use: "id" },
          ),
          [jwk],
        ),
      /aud/,
    );
    assert.throws(
      () =>
        edge._internal.verifyJwt(
          signJwt(
            pair.privateKey,
            { alg: "RS256", kid: "test-kid" },
            { iss: edge._internal.CONFIG.issuer, aud: "client-test", exp: now - 10, token_use: "id" },
          ),
          [jwk],
        ),
      /expired/,
    );
    assert.throws(
      () =>
        edge._internal.verifyJwt(
          signJwt(
            pair.privateKey,
            { alg: "RS256", kid: "test-kid" },
            {
              iss: edge._internal.CONFIG.issuer,
              aud: "client-test",
              exp: now + 120,
              token_use: "id",
              nonce: "wrong",
            },
          ),
          [jwk],
          "nonce-1",
        ),
      /nonce/,
    );
    const otherKey = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 }).privateKey;
    assert.throws(
      () =>
        edge._internal.verifyJwt(
          signJwt(otherKey, { alg: "RS256", kid: "test-kid" }, {
            iss: edge._internal.CONFIG.issuer,
            aud: "client-test",
            exp: now + 120,
            token_use: "id",
          }),
          [jwk],
        ),
      /sig/,
    );
  });

  it("parses cookies without exposing missing names", () => {
    const parsed = edge._internal.parseCookies("__Host-SpiderId=abc; other=1");
    assert.strictEqual(parsed["__Host-SpiderId"], "abc");
    assert.strictEqual(parsed.missing, undefined);
  });

  it("builds a S256 PKCE challenge", () => {
    const challenge = edge._internal.pkceChallenge("verifier");
    assert.strictEqual(challenge.length > 20, true);
  });
});
