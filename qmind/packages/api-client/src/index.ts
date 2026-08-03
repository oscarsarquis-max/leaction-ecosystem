/**
 * @qmind/api-client — public surface for QMind apps.
 *
 * Generation: `npm run generate:api-client` (from qmind/)
 * Do not edit `src/generated/**`.
 */

export {
  createQmindClient,
  type QmindClient,
  type QmindClientOptions,
  type TokenProvider,
  type OrganizationIdProvider,
} from "./client.js";

export {
  QmindApiError,
  type ErrorBody,
  type FieldError,
  isErrorBody,
  parseErrorResponse,
} from "./errors.js";

export type {
  AssessmentOut,
  AssessmentCreate,
  AssessmentStatus,
  OrganizationOut,
  MembershipOut,
  FindingOut,
  ReportOut,
  MaturityPackageOut,
  ActionPlanOut,
  ActionItemOut,
} from "./generated/types.gen.js";
