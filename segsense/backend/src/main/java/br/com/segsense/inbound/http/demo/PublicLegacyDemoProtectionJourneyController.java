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
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Labeled compatibility route for the pre-PRM_016 HTTP prove. Not the public journey. */
@RestController
@Profile({"local", "test"})
@ConditionalOnProperty(name = "segsense.demo.protection-journey.enabled", havingValue = "true")
@RequestMapping("/api/v1/public/demo/legacy-protection-journeys")
public class PublicLegacyDemoProtectionJourneyController {

  private final SubmitDemoProtectionJourneyUseCase journeys;

  public PublicLegacyDemoProtectionJourneyController(SubmitDemoProtectionJourneyUseCase journeys) {
    this.journeys = journeys;
  }

  @PostMapping
  public ResponseEntity<Map<String, Object>> submit(
      @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
      @RequestBody(required = false) Map<String, String> body) {
    String objective = body == null ? null : body.get("declaredObjective");
    DemoProtectionJourney journey =
        journeys.executeLegacy(
            objective,
            CorrelationContext.current() == null
                ? UUID.randomUUID().toString()
                : CorrelationContext.current().toString(),
            idempotencyKey);
    return ResponseEntity.ok().headers(NonStoreHeaders.of()).body(projection(journey));
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
          "legacyLabeledRoute",
          true,
          "notCommercial",
          true,
          "demoSliceOnly",
          true);
    }
  }
}
