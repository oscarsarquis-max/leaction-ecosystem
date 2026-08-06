import {
  getQmindClient,
  withTenantGeneration,
  QmindApiError,
} from "@/api/qmindApi";
import {
  normalizeContext,
  type GuidedAnswerUpsert,
  type GuidedCatalog,
  type GuidedSession,
  type GuidedStep,
} from "@/api/guidedTypes";

function asSession(data: unknown): GuidedSession {
  const s = data as GuidedSession;
  return {
    ...s,
    context: normalizeContext(s.context),
    answers: Array.isArray(s.answers) ? s.answers : [],
  };
}

export async function fetchGuidedCatalog(
  version?: string | null,
): Promise<GuidedCatalog> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: "/api/v1/guided/catalog",
      query: version ? { version } : {},
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as GuidedCatalog;
  });
}

export async function getOrCreateGuidedSession(
  assessmentId: string,
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: `/api/v1/assessments/${assessmentId}/guided`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export async function patchGuidedSession(
  assessmentId: string,
  body: {
    context?: Record<string, unknown>;
    current_step?: GuidedStep;
    current_question_id?: string | null;
  },
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.patch({
      url: `/api/v1/assessments/${assessmentId}/guided`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export async function patchGuidedPosition(
  assessmentId: string,
  body: { current_step: GuidedStep; current_question_id?: string | null },
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.patch({
      url: `/api/v1/assessments/${assessmentId}/guided/position`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export async function upsertGuidedAnswer(
  assessmentId: string,
  questionId: string,
  body: GuidedAnswerUpsert,
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.put({
      url: `/api/v1/assessments/${assessmentId}/guided/answers/${encodeURIComponent(questionId)}`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

function answerBase(assessmentId: string, questionId: string): string {
  return `/api/v1/assessments/${assessmentId}/guided/answers/${encodeURIComponent(questionId)}`;
}

export async function linkGuidedAnswerEvidence(
  assessmentId: string,
  questionId: string,
  evidenceId: string,
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `${answerBase(assessmentId, questionId)}/evidences/link`,
      body: { evidence_id: evidenceId },
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export async function unlinkGuidedAnswerEvidence(
  assessmentId: string,
  questionId: string,
  evidenceId: string,
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.delete({
      url: `${answerBase(assessmentId, questionId)}/evidences/${evidenceId}`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export async function completeGuidedAnswerEvidenceLink(
  assessmentId: string,
  questionId: string,
  evidenceId: string,
): Promise<GuidedSession> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `${answerBase(assessmentId, questionId)}/evidences/${evidenceId}/complete`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return asSession(res.data);
  });
}

export function isGuidedApiError(err: unknown): err is QmindApiError {
  return err instanceof QmindApiError;
}
