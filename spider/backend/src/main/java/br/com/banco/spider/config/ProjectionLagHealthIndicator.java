package br.com.banco.spider.config;

import br.com.banco.spider.operational.observation.OperationalObservation;
import java.time.Duration;
import java.time.Instant;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** Atraso do projetor é degradação do Monitor, não da Spider. */
@Component("projectionLag")
@ConditionalOnProperty(name = "spider.plane", havingValue = "projector")
public class ProjectionLagHealthIndicator implements HealthIndicator {

  private final OperationalObservation observation;

  public ProjectionLagHealthIndicator(OperationalObservation observation) {
    this.observation = observation;
  }

  @Override
  public Health health() {
    int pending = observation.pending();
    int dead = observation.dead();
    Instant oldest = observation.oldestPendingAt();
    Duration age = oldest == null ? Duration.ZERO : Duration.between(oldest, Instant.now());
    Health.Builder builder = dead > 0 ? Health.down() : Health.up();
    return builder
        .withDetail("pending", pending)
        .withDetail("dead", dead)
        .withDetail("oldestPendingSeconds", age.toSeconds())
        .build();
  }
}
