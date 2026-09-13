package br.com.segsense.inbound.http.demo;

import br.com.segsense.application.correlation.CorrelationContext;
import br.com.segsense.application.demo.DemoProjectionJson;
import br.com.segsense.application.demo.SubmitDemoProtectionJourneyUseCase;
import br.com.segsense.domain.demo.DemoProtectionJourney;
import br.com.segsense.inbound.http.link.NonStoreHeaders;
import java.util.Map;
import java.util.UUID;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Profile;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
@RequestMapping("/api/v1/public/demo/protection-journeys")
public class PublicDemoProtectionJourneyController {

  private final SubmitDemoProtectionJourneyUseCase journeys;

  public PublicDemoProtectionJourneyController(SubmitDemoProtectionJourneyUseCase journeys) {
    this.journeys = journeys;
  }

  @PostMapping
  public ResponseEntity<Map<String, Object>> submit(
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
      @RequestBody(required = false) Map<String, String> body) {
    String objective = body == null ? null : body.get("declaredObjective");
    DemoProtectionJourney journey =
        journeys.execute(
            objective,
            CorrelationContext.current() == null
                ? java.util.UUID.randomUUID().toString()
                : CorrelationContext.current().toString(),
            idempotencyKey);
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(projection(journey));
  }

  @GetMapping("/{id}")
  public ResponseEntity<Map<String, Object>> get(@PathVariable UUID id) {
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(projection(journeys.get(id)));
  }

  private Map<String, Object> projection(DemoProtectionJourney journey) {
    try {
      return DemoProjectionJson.readObject(journey.projectionJson());
    } catch (RuntimeException ignored) {
      return Map.of(
          "id",
          journey.id().toString(),
          "status",
          journey.status(),
          "notCommercial",
          true,
          "demoSliceOnly",
          true);
    }
  }
}
