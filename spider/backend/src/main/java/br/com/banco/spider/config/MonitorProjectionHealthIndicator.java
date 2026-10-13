package br.com.banco.spider.config;

import br.com.banco.spider.operational.monitor.MonitorProjectionService;
import com.zaxxer.hikari.HikariDataSource;
import java.util.Locale;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class MonitorProjectionHealthIndicator implements HealthIndicator {

  private final MonitorProjectionService service;
  private final String mode;
  private final ObjectProvider<HikariDataSource> monitorDataSource;

  public MonitorProjectionHealthIndicator(
      MonitorProjectionService service,
      @Value("${spider.monitor.persistence.mode:memory}") String mode,
      ObjectProvider<HikariDataSource> monitorDataSource) {
    this.service = service;
    this.mode = mode == null ? "memory" : mode.trim().toLowerCase(Locale.ROOT);
    this.monitorDataSource = monitorDataSource;
  }

  @Override
  public Health health() {
    if (!service.available()) {
      return Health.down().withDetail("store", "missing").build();
    }
    if ("jpa".equals(mode)) {
      HikariDataSource dataSource = monitorDataSource.getIfAvailable();
      if (dataSource == null) {
        return Health.down().withDetail("store", "datasource-missing").build();
      }
      try {
        Integer one = new JdbcTemplate(dataSource).queryForObject("select 1", Integer.class);
        if (one == null || one != 1) {
          return Health.down().withDetail("store", "ping-failed").build();
        }
      } catch (Exception e) {
        return Health.down().withDetail("store", "unavailable").build();
      }
    }
    return Health.up()
        .withDetail("durable", service.durable())
        .withDetail("mode", mode)
        .build();
  }
}
