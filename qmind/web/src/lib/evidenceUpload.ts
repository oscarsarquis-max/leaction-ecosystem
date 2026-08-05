/**
 * Evidence authorize → PUT → receive.
 * Signed URLs are kept only in local variables for the PUT — never persisted.
 * Completion is only after successful receive (quarantined).
 */

import { getConfig } from "@/config/env";
import { createTrackedAbortController } from "@/api/abortRegistry";
import {
  getActiveOrganizationId,
  getRequestGeneration,
} from "@/api/tenantContext";
import {
  getQmindClient,
  StaleTenantResponseError,
  QmindApiError,
} from "@/api/qmindApi";
import { newIdempotencyKey } from "@/lib/idempotency";
import { validateEvidenceFile } from "@/lib/evidenceConstraints";

export type EvidenceUploadPhase =
  | "idle"
  | "authorizing"
  | "uploading"
  | "confirming"
  | "done"
  | "failed";

export type EvidenceLinkTarget = {
  target_type: "requirement" | "question" | "interview" | "answer";
  target_id: string;
};

export type EvidenceUploadResult = {
  evidenceId: string;
  status: string;
};

function apiOrigin(): string {
  const base = getConfig().apiBaseUrl;
  return base || window.location.origin;
}

function assertTenantFresh(gen: number, orgId: string | null): void {
  if (getRequestGeneration() !== gen) {
    throw new StaleTenantResponseError();
  }
  const nextOrg = getActiveOrganizationId();
  if (orgId && nextOrg && orgId !== nextOrg) {
    throw new StaleTenantResponseError();
  }
}

async function authHeadersForRawFetch(): Promise<HeadersInit> {
  const cfg = getConfig();
  const headers: Record<string, string> = {
    "X-Organization-Id": getActiveOrganizationId() ?? "",
  };
  if (cfg.authMode === "dev") {
    headers["X-Dev-User-Sub"] = cfg.devAuth.sub;
    headers["X-Dev-User-Email"] = cfg.devAuth.email;
  }
  return headers;
}

async function putObject(
  uploadUrl: string,
  method: string,
  headers: Record<string, string>,
  file: File,
  evidenceId: string,
  signal: AbortSignal,
): Promise<void> {
  // memory:// cannot be fetched from the browser — use local bytes endpoint.
  if (uploadUrl.startsWith("memory://")) {
    const putRes = await fetch(`${apiOrigin()}/api/v1/evidences/${evidenceId}/bytes`, {
      method: "PUT",
      headers: {
        ...(await authHeadersForRawFetch()),
        "Content-Type": file.type || "application/octet-stream",
      },
      body: file,
      signal,
    });
    if (!putRes.ok) {
      let code = "upload_put_failed";
      let message = `Falha no envio do arquivo (${putRes.status})`;
      let correlation_id = "";
      try {
        const err = (await putRes.json()) as {
          code?: string;
          message?: string;
          correlation_id?: string;
        };
        code = err.code ?? code;
        message = err.message ?? message;
        correlation_id = err.correlation_id ?? "";
      } catch {
        // keep defaults
      }
      throw new QmindApiError(putRes.status, { code, message, correlation_id });
    }
    return;
  }

  const putRes = await fetch(uploadUrl, {
    method: method || "PUT",
    headers,
    body: file,
    signal,
  });
  if (!putRes.ok) {
    throw new QmindApiError(putRes.status, {
      code: "upload_put_failed",
      message: `Falha no armazenamento do objeto (${putRes.status})`,
      correlation_id: "",
    });
  }
}

export async function uploadEvidenceFile(options: {
  assessmentId: string;
  file: File;
  link?: EvidenceLinkTarget;
  onPhase?: (phase: EvidenceUploadPhase) => void;
}): Promise<EvidenceUploadResult> {
  const validationError = validateEvidenceFile(options.file);
  if (validationError) {
    throw new QmindApiError(422, {
      code: "validation_error",
      message: validationError,
      correlation_id: "",
    });
  }

  const controller = createTrackedAbortController();
  const { signal } = controller;
  const client = getQmindClient();
  const onPhase = options.onPhase ?? (() => undefined);
  const gen = getRequestGeneration();
  const orgId = getActiveOrganizationId();

  try {
    onPhase("authorizing");
    const auth = await client.api.authorizeEvidenceUpload({
      body: {
        assessment_id: options.assessmentId,
        content_type: options.file.type,
        declared_byte_size: options.file.size,
        classification: "confidential",
      },
      headers: { "Idempotency-Key": newIdempotencyKey("ev-auth") },
    });
    assertTenantFresh(gen, orgId);

    const evidence = auth.data!.evidence;
    const upload = auth.data!.upload;
    // Ephemeral — do not assign upload.url to React state / storage.
    const uploadUrl = upload.url;
    const uploadMethod = upload.method;
    const uploadHeaders = { ...upload.headers };

    onPhase("uploading");
    await putObject(
      uploadUrl,
      uploadMethod,
      uploadHeaders,
      options.file,
      evidence.id,
      signal,
    );
    assertTenantFresh(gen, orgId);

    onPhase("confirming");
    const received = await client.api.receiveEvidenceUpload({
      path: { evidence_id: evidence.id },
    });
    assertTenantFresh(gen, orgId);
    const status = received.data!.evidence.status;

    if (options.link) {
      await client.api.createEvidenceLink({
        path: { evidence_id: evidence.id },
        body: {
          target_type: options.link.target_type,
          target_id: options.link.target_id,
        },
      });
      assertTenantFresh(gen, orgId);
    }

    onPhase("done");
    return { evidenceId: evidence.id, status };
  } catch (err) {
    onPhase("failed");
    throw err;
  }
}

export async function openEvidencePreview(evidenceId: string): Promise<void> {
  const client = getQmindClient();
  const gen = getRequestGeneration();
  const orgId = getActiveOrganizationId();
  const dl = await client.api.getEvidenceDownloadUrl({
    path: { evidence_id: evidenceId },
  });
  assertTenantFresh(gen, orgId);
  const url = dl.data!.url;
  if (url.startsWith("memory://")) {
    const res = await fetch(`${apiOrigin()}/api/v1/evidences/${evidenceId}/bytes`, {
      headers: await authHeadersForRawFetch(),
    });
    assertTenantFresh(gen, orgId);
    if (!res.ok) {
      throw new QmindApiError(res.status, {
        code: "download_failed",
        message: "Falha ao obter bytes locais da evidência",
        correlation_id: "",
      });
    }
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
