package br.com.segsense.inbound.http.error;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.domain.catalog.CatalogValidationException;
import br.com.segsense.domain.catalog.DuplicateResourceKeyException;
import br.com.segsense.domain.catalog.InvalidStateTransitionException;
import br.com.segsense.domain.catalog.OptimisticConcurrencyException;
import br.com.segsense.domain.catalog.ResourceNotFoundException;
import br.com.segsense.domain.opportunity.InvalidGovernanceTransitionException;
import br.com.segsense.domain.opportunity.InvalidParentStateException;
import br.com.segsense.domain.opportunity.JustificationRequiredException;
import br.com.segsense.domain.opportunity.NoContentChangeException;
import br.com.segsense.domain.opportunity.NotEffectivelyPublishableException;
import br.com.segsense.domain.link.ApprovedRevisionMismatchException;
import br.com.segsense.domain.link.ContextLinkExpiredException;
import br.com.segsense.domain.link.ContextLinkNotFoundException;
import br.com.segsense.domain.link.ContextLinkRevokedException;
import br.com.segsense.domain.link.ContextLinkTemporarilyUnavailableException;
import br.com.segsense.domain.consent.ConsentNoticeNotApprovedException;
import br.com.segsense.domain.consent.ConsentNoticeObsoleteException;
import br.com.segsense.domain.consent.ContextInstanceExpiredException;
import br.com.segsense.domain.consent.ContextInstanceNotFoundException;
import br.com.segsense.domain.consent.ContextInstanceUnauthorizedException;
import br.com.segsense.domain.consent.ContinuityUnavailableException;
import br.com.segsense.domain.consent.IdempotencyKeyRequiredException;
import br.com.segsense.domain.consent.InstanceCredentialNotReplayableException;
import br.com.segsense.domain.consent.InstanceCredentialRequiredException;
import br.com.segsense.domain.consent.InvalidIdempotencyKeyException;
import br.com.segsense.domain.consent.InvalidCollectedValueException;
import br.com.segsense.domain.demonstration.DemonstrationNotPublishedException;
import br.com.segsense.domain.demo.DemoProtectionException;
import br.com.segsense.domain.link.ContextLinkUnavailableException;
import br.com.segsense.domain.link.InvalidPublisherContextException;
import br.com.segsense.domain.link.LinkExpiryInvalidException;
import br.com.segsense.domain.link.OpportunityNotPublishedException;
import br.com.segsense.domain.link.RequiredPublisherContextMissingException;
import br.com.segsense.domain.opportunity.PublicationNotExpiredException;
import br.com.segsense.domain.opportunity.PublicationWindowNotOpenException;
import br.com.segsense.domain.opportunity.RevisionNotCurrentException;
import br.com.segsense.domain.opportunity.SegregationOfDutiesException;
import br.com.segsense.domain.opportunity.StaleOpportunityRevisionException;
import br.com.segsense.domain.opportunity.SubmissionAlreadyOpenException;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class ApiExceptionHandler {

  private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

  @ExceptionHandler(CatalogValidationException.class)
  public ResponseEntity<ApiError> validation(CatalogValidationException exception) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.VALIDATION_ERROR, exception.getMessage(), currentCorrelationId()));
  }

  @ExceptionHandler({
    MethodArgumentNotValidException.class,
    MethodArgumentTypeMismatchException.class,
    HttpMessageNotReadableException.class
  })
  public ResponseEntity<ApiError> invalidInput(Exception ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.VALIDATION_ERROR,
                "Os dados enviados são inválidos.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ResourceNotFoundException.class)
  public ResponseEntity<ApiError> catalogNotFound(ResourceNotFoundException ignored) {
    return notFoundBody();
  }

  @ExceptionHandler(NoResourceFoundException.class)
  public ResponseEntity<ApiError> notFound(NoResourceFoundException ignored) {
    return notFoundBody();
  }

  @ExceptionHandler(DuplicateResourceKeyException.class)
  public ResponseEntity<ApiError> duplicate(DuplicateResourceKeyException exception) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(ApiError.of(exception.code(), exception.getMessage(), currentCorrelationId()));
  }

  @ExceptionHandler({
    OptimisticConcurrencyException.class,
    ObjectOptimisticLockingFailureException.class
  })
  public ResponseEntity<ApiError> concurrent(Exception ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.CONCURRENT_MODIFICATION,
                "O recurso foi alterado por outra operação. Recarregue e tente novamente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidStateTransitionException.class)
  public ResponseEntity<ApiError> invalidTransition(InvalidStateTransitionException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.INVALID_STATE_TRANSITION,
                "A transição de estado solicitada não é permitida.",
                currentCorrelationId()));
  }

  @ExceptionHandler(StaleOpportunityRevisionException.class)
  public ResponseEntity<ApiError> staleRevision(StaleOpportunityRevisionException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.STALE_OPPORTUNITY_REVISION,
                "A revisão de base não é a revisão corrente da oportunidade.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidParentStateException.class)
  public ResponseEntity<ApiError> invalidParent(InvalidParentStateException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.INVALID_PARENT_STATE,
                "A oportunidade só pode ser criada quando o publicador, o canal e o ambiente estão ativos e disponíveis.",
                currentCorrelationId()));
  }

  @ExceptionHandler(NoContentChangeException.class)
  public ResponseEntity<ApiError> noContentChange(NoContentChangeException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.NO_CONTENT_CHANGE,
                "O conteúdo informado é idêntico ao da revisão vigente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidGovernanceTransitionException.class)
  public ResponseEntity<ApiError> invalidGovernance(InvalidGovernanceTransitionException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.INVALID_GOVERNANCE_TRANSITION,
                "A transição de governança solicitada não é permitida neste estado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(RevisionNotCurrentException.class)
  public ResponseEntity<ApiError> revisionNotCurrent(RevisionNotCurrentException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.REVISION_NOT_CURRENT,
                "A revisão informada não é a revisão submetida corrente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(SubmissionAlreadyOpenException.class)
  public ResponseEntity<ApiError> submissionOpen(SubmissionAlreadyOpenException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.SUBMISSION_ALREADY_OPEN,
                "Já existe uma submissão aberta para esta oportunidade.",
                currentCorrelationId()));
  }

  @ExceptionHandler(SegregationOfDutiesException.class)
  public ResponseEntity<ApiError> segregation(SegregationOfDutiesException ignored) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN)
        .body(
            ApiError.of(
                ApiErrorCodes.SEGREGATION_OF_DUTIES_VIOLATION,
                "A mesma pessoa não pode executar este papel nesta revisão.",
                currentCorrelationId()));
  }

  @ExceptionHandler(JustificationRequiredException.class)
  public ResponseEntity<ApiError> justification(JustificationRequiredException ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.JUSTIFICATION_REQUIRED,
                "Informe uma justificativa administrativa de 10 a 500 caracteres, sem dados pessoais.",
                currentCorrelationId()));
  }

  @ExceptionHandler(NotEffectivelyPublishableException.class)
  public ResponseEntity<ApiError> notPublishable(NotEffectivelyPublishableException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.NOT_EFFECTIVELY_PUBLISHABLE,
                "A hierarquia não está efetivamente disponível para autorizar a publicação.",
                currentCorrelationId()));
  }

  @ExceptionHandler(PublicationWindowNotOpenException.class)
  public ResponseEntity<ApiError> windowClosed(PublicationWindowNotOpenException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.PUBLICATION_WINDOW_NOT_OPEN,
                "A janela temporal da revisão não está aberta em UTC.",
                currentCorrelationId()));
  }

  @ExceptionHandler(PublicationNotExpiredException.class)
  public ResponseEntity<ApiError> notExpired(PublicationNotExpiredException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.PUBLICATION_NOT_EXPIRED,
                "A oportunidade só pode expirar depois de validUntil em UTC.",
                currentCorrelationId()));
  }

  @ExceptionHandler(OpportunityNotPublishedException.class)
  public ResponseEntity<ApiError> opportunityNotPublished(OpportunityNotPublishedException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.OPPORTUNITY_NOT_PUBLISHED,
                "A oportunidade precisa estar publicada e efetiva para emitir um link.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ApprovedRevisionMismatchException.class)
  public ResponseEntity<ApiError> approvedRevisionMismatch(ApprovedRevisionMismatchException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.APPROVED_REVISION_MISMATCH,
                "A revisão aprovada não é a revisão corrente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(LinkExpiryInvalidException.class)
  public ResponseEntity<ApiError> linkExpiry(LinkExpiryInvalidException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.LINK_EXPIRY_INVALID,
                "A expiração do link é inválida em relação à revisão ou ao prazo máximo.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidPublisherContextException.class)
  public ResponseEntity<ApiError> invalidPublisherContext(InvalidPublisherContextException ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.INVALID_PUBLISHER_CONTEXT,
                "O contexto do publicador é inválido para a revisão aprovada.",
                currentCorrelationId()));
  }

  @ExceptionHandler(RequiredPublisherContextMissingException.class)
  public ResponseEntity<ApiError> missingPublisherContext(
      RequiredPublisherContextMissingException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.REQUIRED_PUBLISHER_CONTEXT_MISSING,
                "Há campos obrigatórios do publicador sem valor vinculado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextLinkNotFoundException.class)
  public ResponseEntity<ApiError> contextLinkNotFound(ContextLinkNotFoundException ignored) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_LINK_NOT_FOUND,
                "O link contextual não foi encontrado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextLinkRevokedException.class)
  public ResponseEntity<ApiError> contextLinkRevoked(ContextLinkRevokedException ignored) {
    return ResponseEntity.status(HttpStatus.GONE)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_LINK_REVOKED,
                "Este link contextual foi revogado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextLinkExpiredException.class)
  public ResponseEntity<ApiError> contextLinkExpired(ContextLinkExpiredException ignored) {
    return ResponseEntity.status(HttpStatus.GONE)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_LINK_EXPIRED,
                "Este link contextual não está mais vigente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextLinkUnavailableException.class)
  public ResponseEntity<ApiError> contextLinkUnavailable(ContextLinkUnavailableException ignored) {
    return ResponseEntity.status(HttpStatus.GONE)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_LINK_UNAVAILABLE,
                "Este link contextual não está disponível.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextLinkTemporarilyUnavailableException.class)
  public ResponseEntity<ApiError> contextLinkTemporarilyUnavailable(
      ContextLinkTemporarilyUnavailableException ignored) {
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
        .header("Retry-After", String.valueOf(ignored.retryAfterSeconds()))
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_LINK_TEMPORARILY_UNAVAILABLE,
                "Este link contextual está temporariamente indisponível.",
                currentCorrelationId()));
  }

  @ExceptionHandler(IdempotencyKeyRequiredException.class)
  public ResponseEntity<ApiError> idempotencyRequired(IdempotencyKeyRequiredException ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.IDEMPOTENCY_KEY_REQUIRED,
                "Informe uma chave de idempotência válida para iniciar esta sessão.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidIdempotencyKeyException.class)
  public ResponseEntity<ApiError> idempotencyInvalid(InvalidIdempotencyKeyException ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.IDEMPOTENCY_KEY_INVALID,
                "A chave de idempotência é inválida. Gere uma nova chave e tente novamente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InstanceCredentialNotReplayableException.class)
  public ResponseEntity<ApiError> credentialNotReplayable(InstanceCredentialNotReplayableException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.INSTANCE_CREDENTIAL_NOT_REPLAYABLE,
                "A resposta inicial desta sessão não pode ser recuperada. Comece uma nova tentativa com uma nova chave.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InstanceCredentialRequiredException.class)
  public ResponseEntity<ApiError> instanceCredentialRequired(InstanceCredentialRequiredException ignored) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
        .body(
            ApiError.of(
                ApiErrorCodes.INSTANCE_CREDENTIAL_REQUIRED,
                "A continuidade desta sessão não pôde ser confirmada.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextInstanceNotFoundException.class)
  public ResponseEntity<ApiError> instanceNotFound(ContextInstanceNotFoundException ignored) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_INSTANCE_NOT_FOUND,
                "Esta sessão contextual não foi encontrada.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextInstanceExpiredException.class)
  public ResponseEntity<ApiError> instanceExpired(ContextInstanceExpiredException ignored) {
    return ResponseEntity.status(HttpStatus.GONE)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_INSTANCE_EXPIRED,
                "Esta sessão contextual não está mais vigente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContextInstanceUnauthorizedException.class)
  public ResponseEntity<ApiError> instanceUnauthorized(ContextInstanceUnauthorizedException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTEXT_INSTANCE_UNAUTHORIZED,
                "Esta escolha não pode ser registrada neste estado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(InvalidCollectedValueException.class)
  public ResponseEntity<ApiError> invalidCollected(InvalidCollectedValueException ignored) {
    return ResponseEntity.status(HttpStatus.BAD_REQUEST)
        .body(
            ApiError.of(
                ApiErrorCodes.INVALID_COLLECTED_VALUE,
                "Há informações inválidas ou não permitidas nesta etapa.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ContinuityUnavailableException.class)
  public ResponseEntity<ApiError> continuityUnavailable(ContinuityUnavailableException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.CONTINUITY_UNAVAILABLE,
                "A continuidade desta jornada ainda não está disponível.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ConsentNoticeNotApprovedException.class)
  public ResponseEntity<ApiError> noticeNotApproved(ConsentNoticeNotApprovedException ignored) {
    return ResponseEntity.status(HttpStatus.UNPROCESSABLE_ENTITY)
        .body(
            ApiError.of(
                ApiErrorCodes.CONSENT_NOTICE_NOT_APPROVED,
                "O aviso de finalidade ainda não está aprovado.",
                currentCorrelationId()));
  }

  @ExceptionHandler(ConsentNoticeObsoleteException.class)
  public ResponseEntity<ApiError> noticeObsolete(ConsentNoticeObsoleteException ignored) {
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.CONSENT_NOTICE_OBSOLETE,
                "O aviso de finalidade desta sessão não corresponde à versão vigente.",
                currentCorrelationId()));
  }

  @ExceptionHandler(DemoProtectionException.class)
  public ResponseEntity<ApiError> demoProtection(DemoProtectionException exception) {
    return ResponseEntity.status(exception.httpStatus())
        .headers(br.com.segsense.inbound.http.link.NonStoreHeaders.of())
        .body(ApiError.of(exception.code(), exception.getMessage(), currentCorrelationId()));
  }

  @ExceptionHandler(DemonstrationNotPublishedException.class)
  public ResponseEntity<ApiError> demonstrationNotPublished(DemonstrationNotPublishedException ignored) {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .headers(br.com.segsense.inbound.http.link.NonStoreHeaders.of())
        .body(
            ApiError.of(
                ApiErrorCodes.DEMONSTRATION_NOT_PUBLISHED,
                "Não há conteúdo editorial publicado para esta demonstração.",
                currentCorrelationId()));
  }

  @ExceptionHandler(DataIntegrityViolationException.class)
  public ResponseEntity<ApiError> integrity(DataIntegrityViolationException ignored) {
    log.warn("event=persistence_conflict");
    return ResponseEntity.status(HttpStatus.CONFLICT)
        .body(
            ApiError.of(
                ApiErrorCodes.CONCURRENT_MODIFICATION,
                "Não foi possível persistir o recurso.",
                currentCorrelationId()));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<ApiError> unexpected(Exception exception) {
    log.error("event=unhandled_exception type={}", exception.getClass().getSimpleName());
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
        .body(
            ApiError.of(
                ApiErrorCodes.INTERNAL_ERROR,
                "Não foi possível concluir a solicitação.",
                currentCorrelationId()));
  }

  private static ResponseEntity<ApiError> notFoundBody() {
    return ResponseEntity.status(HttpStatus.NOT_FOUND)
        .body(
            ApiError.of(
                ApiErrorCodes.NOT_FOUND,
                "O recurso solicitado não foi encontrado.",
                currentCorrelationId()));
  }

  private static String currentCorrelationId() {
    UUID correlationId = CorrelationContext.current();
    return correlationId == null ? null : correlationId.toString();
  }
}
