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
  AssessmentType,
  ScopeItemIn,
  ScopeOut,
  TeamMemberIn,
  TeamMemberOut,
  OrganizationOut,
  MembershipOut,
  FindingOut,
  ReportOut,
  MaturityPackageOut,
  ActionPlanOut,
  ActionItemOut,
  ActionItemStatus,
  ActionKind,
  ImprovementCaseCreate,
  ImprovementCaseOut,
  ImprovementCasePatch,
  ImprovementCaseAnalysisRunOut,
  ImprovementCaseActionsOut,
  ImprovementCaseEvolutionOut,
  ExecutionIntelligenceRunOut,
  ExecutionIntelligenceResult,
  ExecutionSignal,
  FindingActionCreate,
  OutcomeObservationCreate,
  OutcomeObservationOut,
} from "./generated/types.gen.js";

/** Agile Action Execution Workspace (ISOI-007). */
export type {
  AgendaEventCreate,
  AgendaEventOut,
  BoardCardOut,
  BoardColumnOut,
  BoardMoveIn,
  BoardMoveOut,
  BoardOut,
  CarryDecisionIn,
  CeremonyRecordCreate,
  CeremonyRecordOut,
  CheckInCreate,
  CheckInOut,
  DependencyCreate,
  DependencyOut,
  ImpedimentCreate,
  ImpedimentOut,
  ImpedimentUpdate,
  SprintActivateIn,
  SprintCompleteIn,
  SprintCreate,
  SprintMetricsOut,
  SprintOut,
  SquadCreate,
  SquadMembershipCreate,
  SquadMembershipOut,
  SquadMembershipUpdate,
  SquadOut,
} from "./generated/types.gen.js";

/** Evidence and result measurement (ISOI-008). */
export type {
  BaselineStatus,
  ContextualAuthorizeUploadIn,
  EvidenceAttachmentOut,
  EvidenceLinkOut,
  EvidenceLinkTargetType,
  EvidenceOut,
  EvidenceStatus,
  IndicatorCreate,
  IndicatorDirection,
  IndicatorOut,
  IndicatorReviseIn,
  IndicatorStatus,
  IndicatorUnitKind,
  MeasurementCorrectionIn,
  MeasurementKind,
  MeasurementPlanCreate,
  MeasurementPlanOut,
  MeasurementPlanStatus,
  MeasurementPosture,
  MeasurementRecordCreate,
  MeasurementRecordOut,
  MeasurementSummary,
  MeasurementSummaryOut,
  SubstantiationLevel,
  TargetEvaluationOut,
  TargetEvaluationState,
  TargetPosture,
} from "./generated/types.gen.js";
