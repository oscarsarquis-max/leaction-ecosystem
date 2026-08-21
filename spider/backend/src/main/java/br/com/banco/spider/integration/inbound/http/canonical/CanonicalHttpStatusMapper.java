package br.com.banco.spider.integration.inbound.http.canonical;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.signal.ExternalSignalProcessingStatus;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;

@Component
public class CanonicalHttpStatusMapper {

  public HttpStatus fromExecutionResult(CanonicalExecutionResult result) {
    if (result == null) {
      return HttpStatus.INTERNAL_SERVER_ERROR;
    }
    ExecutionState state = result.state();
    if (state == ExecutionState.SUCCEEDED) {
      return HttpStatus.OK;
    }
    if (state == ExecutionState.RUNNING
        || state == ExecutionState.WAITING_EXTERNAL
        || state == ExecutionState.PLANNED
        || state == ExecutionState.RECEIVED
        || state == ExecutionState.VALIDATED
        || state == ExecutionState.RESOLVED) {
      return HttpStatus.ACCEPTED;
    }
    if (state == ExecutionState.REJECTED) {
      return fromError(result.errors().isEmpty() ? null : result.errors().getFirst());
    }
    if (state == ExecutionState.TIMED_OUT) {
      return HttpStatus.GATEWAY_TIMEOUT;
    }
    return HttpStatus.INTERNAL_SERVER_ERROR;
  }

  public HttpStatus fromError(CanonicalError error) {
    if (error == null) {
      return HttpStatus.INTERNAL_SERVER_ERROR;
    }
    return switch (error.category()) {
      case VALIDATION, CONTRACT -> HttpStatus.BAD_REQUEST;
      case AUTHENTICATION -> HttpStatus.UNAUTHORIZED;
      case AUTHORIZATION -> HttpStatus.FORBIDDEN;
      case IDEMPOTENCY -> HttpStatus.CONFLICT;
      case RESOLUTION -> HttpStatus.UNPROCESSABLE_ENTITY;
      case UNAVAILABLE -> HttpStatus.SERVICE_UNAVAILABLE;
      case TIMEOUT -> HttpStatus.GATEWAY_TIMEOUT;
      default -> HttpStatus.INTERNAL_SERVER_ERROR;
    };
  }

  public HttpStatus fromSignalStatus(ExternalSignalProcessingStatus status) {
    return switch (status) {
      case ACCEPTED_AND_RESUMED, ACCEPTED_AND_TERMINATED, DUPLICATE -> HttpStatus.OK;
      case CONFLICT -> HttpStatus.CONFLICT;
      case REJECTED -> HttpStatus.BAD_REQUEST;
      case LATE_REJECTED, ORPHANED -> HttpStatus.ACCEPTED;
    };
  }

  public HttpStatus fromHint(String hint, CanonicalError error) {
    if ("401".equals(hint)) {
      return HttpStatus.UNAUTHORIZED;
    }
    if ("403".equals(hint)) {
      return HttpStatus.FORBIDDEN;
    }
    if ("409".equals(hint)) {
      return HttpStatus.CONFLICT;
    }
    if ("400".equals(hint)) {
      return HttpStatus.BAD_REQUEST;
    }
    return fromError(error);
  }
}
