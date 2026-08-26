/** Thin API client for Playwright — same headers as Vite/dev auth. */

export type ApiClient = {
  baseURL: string;
  orgId: string;
  membershipId: string;
  request: (
    method: string,
    path: string,
    opts?: { body?: unknown; headers?: Record<string, string>; rawBody?: BodyInit },
  ) => Promise<{ status: number; json: any; text: string }>;
};

const MODEL = "c1000000-0000-4000-8000-000000000001";
const STANDARD = "b1000000-0000-4000-8000-000000000002";
const REQUIREMENT = "b1000000-0000-4000-8000-000000000010";

export function catalogIds() {
  return { MODEL, STANDARD, REQUIREMENT };
}

export async function createApi(
  baseURL: string,
  orgId: string,
  identity?: { sub: string; email: string },
): Promise<ApiClient> {
  const sub = identity?.sub ?? "dev-local-user";
  const email = identity?.email ?? "dev@example.com";

  async function request(
    method: string,
    path: string,
    o?: { body?: unknown; headers?: Record<string, string>; rawBody?: BodyInit },
  ) {
    const headers: Record<string, string> = {
      "X-Dev-User-Sub": sub,
      "X-Dev-User-Email": email,
      "X-Organization-Id": orgId,
      ...(o?.headers ?? {}),
    };
    let body: BodyInit | undefined = o?.rawBody;
    if (o?.body !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(o.body);
    }
    const res = await fetch(`${baseURL}${path}`, { method, headers, body });
    const text = await res.text();
    let json: any = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = null;
    }
    return { status: res.status, json, text };
  }

  const mem = await request("GET", "/api/v1/organizations/me/memberships");
  if (mem.status !== 200) {
    throw new Error(`memberships failed: ${mem.status} ${mem.text}`);
  }
  const mine = (mem.json as any[]).find((m) => m.organization_id === orgId);
  if (!mine) throw new Error(`no membership for org ${orgId}`);

  return { baseURL, orgId, membershipId: mine.id as string, request };
}

export async function createSecondOrg(
  baseURL: string,
  identity?: { sub: string; email: string },
): Promise<{ orgId: string; name: string }> {
  const sub = identity?.sub ?? "dev-local-user";
  const email = identity?.email ?? "dev@example.com";
  const name = `QMind E2E Org B ${Date.now()}`;
  const res = await fetch(`${baseURL}/api/v1/organizations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Dev-User-Sub": sub,
      "X-Dev-User-Email": email,
      "Idempotency-Key": `e2e-org-${crypto.randomUUID()}`,
    },
    body: JSON.stringify({ name, timezone: "America/Sao_Paulo" }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`create org: ${res.status} ${JSON.stringify(json)}`);
  return { orgId: json.organization.id as string, name };
}

/** Create assessment with scope; creator is lead. Plan + start → in_progress. */
export async function createStartedAssessment(api: ApiClient): Promise<string> {
  const { MODEL, STANDARD, REQUIREMENT } = catalogIds();
  const created = await api.request("POST", "/api/v1/assessments", {
    body: {
      assessment_model_id: MODEL,
      standard_version_id: STANDARD,
      type: "diagnosis",
      scope: [{ requirement_id: REQUIREMENT }],
    },
    headers: { "Idempotency-Key": `e2e-a-${crypto.randomUUID()}` },
  });
  if (created.status !== 201 && created.status !== 200) {
    throw new Error(`create assessment: ${created.status} ${created.text}`);
  }
  const aid = created.json.id as string;

  let r = await api.request("POST", `/api/v1/assessments/${aid}/transitions/plan`);
  if (r.status >= 400) throw new Error(`plan: ${r.status} ${r.text}`);
  r = await api.request("POST", `/api/v1/assessments/${aid}/transitions/start`);
  if (r.status >= 400) throw new Error(`start: ${r.status} ${r.text}`);
  return aid;
}

export async function uploadApproveEvidence(api: ApiClient, assessmentId: string) {
  const bytes = new TextEncoder().encode("%PDF-1.4 qmind-e2e");
  const auth = await api.request("POST", "/api/v1/evidences/authorize", {
    body: {
      assessment_id: assessmentId,
      content_type: "application/pdf",
      declared_byte_size: bytes.byteLength,
      classification: "internal",
    },
    headers: { "Idempotency-Key": `e2e-ev-${crypto.randomUUID()}` },
  });
  if (auth.status >= 400) throw new Error(`authorize: ${auth.status} ${auth.text}`);
  const eid = auth.json.evidence.id as string;

  const put = await api.request("PUT", `/api/v1/evidences/${eid}/bytes`, {
    rawBody: bytes,
    headers: { "Content-Type": "application/pdf" },
  });
  if (put.status >= 400) throw new Error(`put bytes: ${put.status} ${put.text}`);

  const recv = await api.request(
    "POST",
    `/api/v1/evidences/${eid}/transitions/receive`,
  );
  if (recv.status >= 400) throw new Error(`receive: ${recv.status} ${recv.text}`);

  const ap = await api.request(
    "POST",
    `/api/v1/evidences/${eid}/transitions/security_pass`,
  );
  if (ap.status >= 400) throw new Error(`security_pass evidence: ${ap.status} ${ap.text}`);
  return eid;
}

export async function downloadEvidenceOk(api: ApiClient, evidenceId: string) {
  const url = await api.request("GET", `/api/v1/evidences/${evidenceId}/download-url`);
  if (url.status >= 400) throw new Error(`download-url: ${url.status} ${url.text}`);
  const bytes = await fetch(`${api.baseURL}/api/v1/evidences/${evidenceId}/bytes`, {
    headers: {
      "X-Dev-User-Sub": "dev-local-user",
      "X-Dev-User-Email": "dev@example.com",
      "X-Organization-Id": api.orgId,
    },
  });
  if (!bytes.ok) throw new Error(`bytes GET: ${bytes.status}`);
  const buf = await bytes.arrayBuffer();
  return { urlJson: url.json, byteLength: buf.byteLength };
}
