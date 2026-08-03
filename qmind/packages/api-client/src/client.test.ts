import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { createQmindClient } from "./client.js";
import { QmindApiError, isErrorBody } from "./errors.js";

describe("QmindApiError / ErrorBody", () => {
  it("recognizes ErrorBody shape", () => {
    assert.equal(
      isErrorBody({
        code: "not_found",
        message: "missing",
        correlation_id: "11111111-2222-4333-8444-555555555555",
      }),
      true,
    );
    assert.equal(isErrorBody({ message: "x" }), false);
  });

  it("exposes field_errors", () => {
    const err = new QmindApiError(422, {
      code: "validation_error",
      message: "Request validation failed",
      correlation_id: "11111111-2222-4333-8444-555555555555",
      field_errors: [{ field: "body.name", code: "too_short", message: "too short" }],
    });
    assert.equal(err.status, 422);
    assert.equal(err.code, "validation_error");
    assert.equal(err.fieldErrors.length, 1);
  });
});

describe("createQmindClient", () => {
  it("injects Bearer, org header, and maps ErrorBody", async () => {
    const calls: Request[] = [];
    const fetchMock: typeof fetch = async (input) => {
      const req = input instanceof Request ? input : new Request(String(input));
      calls.push(req);
      return new Response(
        JSON.stringify({
          code: "not_found",
          message: "Assessment not found",
          correlation_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    };

    let org = "org-a";
    const client = createQmindClient({
      baseUrl: "http://localhost:8008",
      fetch: fetchMock,
      getAccessToken: async () => "tok-123",
      getOrganizationId: async () => org,
    });

    await assert.rejects(
      () =>
        client.api.getAssessment({
          path: { assessment_id: "11111111-2222-4333-8444-555555555555" },
        }),
      (e: unknown) => {
        assert.ok(e instanceof QmindApiError);
        assert.equal(e.status, 404);
        assert.equal(e.code, "not_found");
        assert.equal(e.correlationId, "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee");
        return true;
      },
    );

    assert.equal(calls.length, 1);
    assert.equal(calls[0]!.headers.get("Authorization"), "Bearer tok-123");
    assert.equal(calls[0]!.headers.get("X-Organization-Id"), "org-a");
    assert.equal(calls[0]!.headers.get("X-QMind-Tenant-Epoch"), "0");

    org = "org-b";
    client.invalidateTenant();
    assert.equal(client.getTenantEpoch(), 1);

    await assert.rejects(() => client.api.getHealth({}));
    assert.equal(calls[1]!.headers.get("X-Organization-Id"), "org-b");
    assert.equal(calls[1]!.headers.get("X-QMind-Tenant-Epoch"), "1");
  });
});
