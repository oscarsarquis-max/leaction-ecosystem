import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { validateEvidenceFile } from "@/lib/evidenceConstraints";
import { uploadEvidenceFile } from "@/lib/evidenceUpload";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext, setActiveOrganizationId } from "@/api/tenantContext";
import { abortAllInFlight } from "@/api/abortRegistry";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "44444444-4444-4444-8444-444444444444";
const EID = "99999999-9999-4999-8999-999999999999";

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("evidence constraints", () => {
  it("rejects disallowed type and oversized files", () => {
    const bad = new File([new Uint8Array([1])], "x.exe", { type: "application/x-msdownload" });
    expect(validateEvidenceFile(bad)).toMatch(/não permitido/i);
    const huge = new File([new Uint8Array(25_000_001)], "big.pdf", { type: "application/pdf" });
    expect(validateEvidenceFile(huge)).toMatch(/limite/i);
  });
});

describe("uploadEvidenceFile", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    resetTenantContext();
    setActiveOrganizationId(ORG);
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_API_BASE_URL", "http://api.test");
  });

  afterEach(() => {
    abortAllInFlight("test_cleanup");
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("authorize → local PUT → receive; never treats upload as done before receive", async () => {
    const phases: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const method = (
        init?.method ||
        (input instanceof Request ? input.method : "GET")
      ).toUpperCase();
      if (url.includes("/evidences/authorize") && method === "POST") {
        return json(
          {
            evidence: {
              id: EID,
              organization_id: ORG,
              assessment_id: AID,
              status: "upload_pending",
              classification: "confidential",
              content_type: "application/pdf",
              byte_size: 4,
              content_hash: null,
              storage_key: "org/x/evidence/y/v1",
              version_no: 1,
              legal_hold: false,
              upload_expires_at: null,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            upload: {
              url: "memory://upload/org/x",
              method: "PUT",
              headers: { "Content-Type": "application/pdf" },
              expires_in_seconds: 900,
            },
          },
          201,
        );
      }
      if (url.includes(`/evidences/${EID}/bytes`) && method === "PUT") {
        return new Response(null, { status: 204 });
      }
      if (url.includes(`/evidences/${EID}/transitions/receive`) && method === "POST") {
        return json({
          evidence: {
            id: EID,
            organization_id: ORG,
            assessment_id: AID,
            status: "quarantined",
            classification: "confidential",
            content_type: "application/pdf",
            byte_size: 4,
            content_hash: "sha256:ab",
            storage_key: "org/x/evidence/y/v1",
            version_no: 1,
            legal_hold: false,
            upload_expires_at: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          from_status: "upload_pending",
          to_status: "quarantined",
          event: "receive",
        });
      }
      return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const file = new File([new Uint8Array([1, 2, 3, 4])], "doc.pdf", {
      type: "application/pdf",
    });
    const result = await uploadEvidenceFile({
      assessmentId: AID,
      file,
      onPhase: (p) => phases.push(p),
    });

    expect(result.status).toBe("quarantined");
    expect(phases).toEqual(["authorizing", "uploading", "confirming", "done"]);
    const receiveIdx = fetchMock.mock.calls.findIndex(([u, i]) => {
      const url = typeof u === "string" ? u : u instanceof URL ? u.href : u.url;
      return url.includes("/receive") && (i?.method === "POST" || !i?.method);
    });
    const putIdx = fetchMock.mock.calls.findIndex(([u, i]) => {
      const url = typeof u === "string" ? u : u instanceof URL ? u.href : u.url;
      return url.includes("/bytes") && i?.method === "PUT";
    });
    expect(putIdx).toBeGreaterThanOrEqual(0);
    expect(receiveIdx).toBeGreaterThan(putIdx);
  });

  it("ignores stale response after tenant switch mid-upload", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const method = (
        init?.method ||
        (input instanceof Request ? input.method : "GET")
      ).toUpperCase();
      if (url.includes("/authorize") && method === "POST") {
        setActiveOrganizationId("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb");
        return json(
          {
            evidence: {
              id: EID,
              organization_id: ORG,
              assessment_id: AID,
              status: "upload_pending",
              classification: "confidential",
              content_type: "application/pdf",
              byte_size: 1,
              content_hash: null,
              storage_key: "k",
              version_no: 1,
              legal_hold: false,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            upload: {
              url: "memory://upload/k",
              method: "PUT",
              headers: {},
              expires_in_seconds: 60,
            },
          },
          201,
        );
      }
      return new Response(null, { status: 204 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const file = new File([new Uint8Array([1])], "a.pdf", { type: "application/pdf" });
    await expect(
      uploadEvidenceFile({ assessmentId: AID, file }),
    ).rejects.toMatchObject({ name: "StaleTenantResponseError" });
  });
});
