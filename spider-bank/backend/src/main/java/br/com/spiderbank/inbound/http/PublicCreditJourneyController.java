package br.com.spiderbank.inbound.http;

import br.com.spiderbank.application.DemoCustomerSessionService;
import br.com.spiderbank.application.GovernedCreditContext;
import br.com.spiderbank.application.SubmitWorkingCapitalJourneyUseCase;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PublicCreditJourneyController {

  private final SubmitWorkingCapitalJourneyUseCase journeys;
  private final DemoCustomerSessionService sessions;

  public PublicCreditJourneyController(
      SubmitWorkingCapitalJourneyUseCase journeys, DemoCustomerSessionService sessions) {
    this.journeys = journeys;
    this.sessions = sessions;
  }

  @GetMapping("/api/credit/context")
  public Map<String, Object> context() {
    return GovernedCreditContext.publicView();
  }

  @PostMapping("/api/credit/demo-session")
  public Map<String, Object> startSession(@RequestBody(required = false) Map<String, String> body) {
    String persona = body == null ? "ok" : body.getOrDefault("persona", "ok");
    return sessions.start(persona);
  }

  @PostMapping("/api/credit/journeys")
  public Map<String, Object> submit(
      @RequestBody JourneyRequest request,
      @RequestHeader(value = "X-Correlation-ID", required = false) String correlationHeader,
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyHeader) {
    JourneyRequest body =
        request == null ? new JourneyRequest(false, null, null, null, null, null) : request;
    String correlation = firstNonBlank(body.correlationId(), correlationHeader);
    String idempotency = firstNonBlank(body.idempotencyKey(), idempotencyHeader);
    return journeys.execute(
        body.confirmed(),
        correlation,
        idempotency,
        body.sessionAssertion(),
        body.principalCents(),
        body.termMonths());
  }

  private static String firstNonBlank(String first, String second) {
    if (first != null && !first.isBlank()) {
      return first;
    }
    return second;
  }

  public record JourneyRequest(
      Boolean objectiveConfirmed,
      String correlationId,
      String idempotencyKey,
      String sessionAssertion,
      Long principalCents,
      Integer termMonths) {
    public boolean confirmed() {
      return Boolean.TRUE.equals(objectiveConfirmed);
    }
  }
}
