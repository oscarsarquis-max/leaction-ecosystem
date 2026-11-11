package br.com.banco.spider.config;

import br.com.banco.spider.operational.monitor.MonitorProjectionPort;
import br.com.banco.spider.operational.observation.ObservationApplier;
import br.com.banco.spider.operational.observation.OperationalObservation;
import javax.sql.DataSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.Scheduled;

@Configuration
public class ObservationConfig {

  @Bean
  @ConditionalOnProperty(name = "spider.observation.dispatch", havingValue = "outbox")
  OperationalObservation operationalObservation(@Qualifier("dataSource") DataSource dataSource) {
    return new OperationalObservation(dataSource);
  }

  @Bean
  @ConditionalOnProperty(name = "spider.plane", havingValue = "projector")
  ObservationProjector observationProjector(
      OperationalObservation observation, MonitorProjectionPort port) {
    return new ObservationProjector(observation, port);
  }

  public static final class ObservationProjector {
    private static final Logger log = LoggerFactory.getLogger(ObservationProjector.class);
    private final OperationalObservation observation;
    private final MonitorProjectionPort port;
    private final ObservationApplier applier = new ObservationApplier();

    ObservationProjector(OperationalObservation observation, MonitorProjectionPort port) {
      this.observation = observation;
      this.port = port;
    }

    @Scheduled(fixedDelayString = "${spider.observation.projector.interval:PT2S}")
    public void drain() {
      for (OperationalObservation.Fact fact : observation.claim(25)) {
        try {
          applier.apply(port, fact.occurredAt(), fact.payload());
          observation.ack(fact.id());
        } catch (RuntimeException exception) {
          log.warn(
              "event=observation_project_failed id={} attempts={} kind={}",
              fact.id(),
              fact.attempts(),
              fact.kind());
          observation.retry(fact.id(), fact.attempts(), exception.getClass().getSimpleName());
        }
      }
    }
  }
}
